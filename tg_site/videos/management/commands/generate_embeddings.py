from django.core.management.base import BaseCommand
from videos.models import Post, EmbeddingGenerator
from django.db.models import Q
from concurrent.futures import ThreadPoolExecutor, as_completed
import time


class Command(BaseCommand):
    help = 'Generate embeddings for posts that dont have them'

    def add_arguments(self, parser):
        parser.add_argument('--batch_size', type=int, default=100)
        parser.add_argument('--limit', type=int, help='Limit number of posts to process')
        parser.add_argument('--force', action='store_true', help='Regenerate all embeddings')
        parser.add_argument('--threads', type=int, default=10, help='Number of concurrent threads')

    def generate_embedding_for_post(self, post):
        max_retries = 5
        for attempt in range(max_retries):
            try:
                embedding = EmbeddingGenerator.generate_embedding(post.text)
                return (post.id, embedding, None)
            except Exception as e:
                error_str = str(e).lower()
                if 'rate' in error_str or '429' in error_str or 'quota' in error_str:
                    wait_time = (2 ** attempt) * 2  # Exponential backoff: 2, 4, 8, 16, 32 seconds
                    if attempt < max_retries - 1:
                        time.sleep(wait_time)
                        continue
                return (post.id, None, str(e))

    def process_batch(self, batch):
        """Process a batch of posts with single API call"""
        try:
            texts = [post.text for post in batch]
            embeddings = EmbeddingGenerator.generate_embeddings_batch(texts)
            return (batch, embeddings, None)
        except Exception as e:
            return (batch, None, str(e))

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        limit = options['limit']
        force = options['force']
        threads = options['threads']
        
        if force:
            queryset = Post.objects.filter(text__isnull=False).exclude(text='')
        else:
            queryset = Post.objects.filter(
                Q(embedding__isnull=True) & Q(text__isnull=False)
            ).exclude(text='')
        
        if limit:
            queryset = queryset[:limit]
        
        total = queryset.count()
        self.stdout.write(f'Processing {total} posts with {threads} parallel batches of {batch_size}...')
        
        processed = 0
        errors = 0
        start_time = time.time()
        
        # Process in super-batches for threading
        super_batch_size = batch_size * threads
        
        for i in range(0, total, super_batch_size):
            super_batch_start = time.time()
            
            # Create sub-batches for parallel processing
            batches = []
            for j in range(i, min(i + super_batch_size, total), batch_size):
                batch = list(queryset[j:j + batch_size])
                if batch:
                    batches.append(batch)
            
            self.stdout.write(f'\n=== Super-batch {i//super_batch_size + 1}: Processing {len(batches)} batches in parallel ===')
            
            # Process batches in parallel
            results = []
            with ThreadPoolExecutor(max_workers=threads) as executor:
                futures = {executor.submit(self.process_batch, batch): batch for batch in batches}
                
                completed = 0
                for future in as_completed(futures):
                    completed += 1
                    self.stdout.write(f'  Batch completed: {completed}/{len(batches)}')
                    results.append(future.result())
            
            # Bulk update all results
            all_posts_to_update = []
            for batch, embeddings, error in results:
                if error:
                    self.stdout.write(self.style.ERROR(f'Batch error: {error}'))
                    errors += len(batch)
                elif embeddings:
                    for post, embedding in zip(batch, embeddings):
                        if embedding:
                            post.embedding = embedding
                            all_posts_to_update.append(post)
            
            if all_posts_to_update:
                Post.objects.bulk_update(all_posts_to_update, ['embedding'], batch_size=500)
                processed += len(all_posts_to_update)
                self.stdout.write(f'✓ Super-batch complete: {len(all_posts_to_update)} embeddings saved')
            
            super_batch_time = time.time() - super_batch_start
            elapsed = time.time() - start_time
            posts_per_sec = processed / elapsed if elapsed > 0 else 0
            remaining = (total - processed) / posts_per_sec if posts_per_sec > 0 else 0
            
            self.stdout.write(
                f'Processed {processed}/{total} ({processed/total*100:.1f}%) | '
                f'{posts_per_sec:.1f} posts/sec | '
                f'Super-batch time: {super_batch_time:.1f}s | '
                f'ETA: {remaining/60:.1f} min | '
                f'Errors: {errors}'
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Done! Processed {processed} posts with {errors} errors in {elapsed/60:.1f} minutes'
            )
        )

