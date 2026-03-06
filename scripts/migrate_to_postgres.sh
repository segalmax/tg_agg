#!/bin/bash
# Migration script: MySQL → PostgreSQL with pgvector
set -e

echo "=== PostgreSQL + pgvector Migration Script ==="
echo ""
echo "Prerequisites:"
echo "1. PostgreSQL service added to Railway"
echo "2. DB credentials in .env file"
echo "3. pgvector extension enabled: CREATE EXTENSION vector;"
echo ""
read -p "Have you completed the prerequisites? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Please complete prerequisites first."
    exit 1
fi

cd "$(dirname "$0")/tg_site"
source ../venv/bin/activate

echo ""
echo "Step 1: Backup MySQL data..."
python manage.py dumpdata videos > ../mysql_backup.json
echo "✓ Backup saved to mysql_backup.json"

echo ""
echo "Step 2: Installing PostgreSQL dependencies..."
pip install -r ../requirements.txt
echo "✓ Dependencies installed"

echo ""
echo "Step 3: Switching to PostgreSQL settings..."
cp config/settings.py config/settings_mysql_backup.py
cp config/settings_postgres.py config/settings.py
echo "✓ Settings updated (backup saved)"

echo ""
echo "Step 4: Running migrations on PostgreSQL..."
python manage.py migrate
echo "✓ Schema created"

echo ""
echo "Step 5: Loading data into PostgreSQL..."
python manage.py loaddata ../mysql_backup.json
echo "✓ Data loaded"

echo ""
echo "Step 6: Updating models with embedding field..."
cp videos/models.py videos/models_old_backup.py
cp videos/models_with_embeddings.py videos/models.py
echo "✓ Models updated (backup saved)"

echo ""
echo "Step 7: Creating migration for embedding field..."
python manage.py makemigrations
python manage.py migrate
echo "✓ Embedding field added"

echo ""
echo "Step 8: Generating embeddings for existing posts..."
echo "This may take a while depending on post count..."
python manage.py generate_embeddings --batch_size=50
echo "✓ Embeddings generated"

echo ""
echo "Step 9: Creating HNSW index for fast search..."
python manage.py dbshell <<EOF
CREATE INDEX ON videos_post USING hnsw (embedding vector_cosine_ops);
EOF
echo "✓ Index created"

echo ""
echo "=== Migration Complete! ==="
echo ""
echo "Next steps:"
echo "1. Test semantic search: python manage.py shell"
echo "   >>> from videos.models import Post"
echo "   >>> results = Post.semantic_search('your query here')"
echo "2. Update Railway environment variables"
echo "3. Deploy to Railway"
echo ""
echo "Files backed up:"
echo "  - mysql_backup.json (data)"
echo "  - config/settings_mysql_backup.py (old settings)"
echo "  - videos/models_old_backup.py (old models)"

