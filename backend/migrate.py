# migrate.py
import os
import sys
import psycopg2

def load_env(env_path):
    """Simple parser for .env file since python-dotenv might not be installed."""
    env_vars = {}
    if not os.path.exists(env_path):
        return env_vars
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                # Strip potential surrounding quotes
                key = key.strip()
                val = val.strip().strip("'").strip('"')
                env_vars[key] = val
    return env_vars

def main():
    # Set CWD to the directory containing migrate.py
    script_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(script_dir, ".env")
    
    print(f"Loading env file from: {env_path}")
    env = load_env(env_path)
    
    db_url = env.get("DATABASE_URL")
    if not db_url:
        print("Error: DATABASE_URL not found in .env file.")
        sys.exit(1)
        
    # Auto-convert IPv6-only hostname to IPv4 pooler in our local agent environment
    if "db.nnapoohhhibyxlebsxqj.supabase.co" in db_url:
        print("Detected IPv6-only Supabase hostname. Mapping to IPv4 pooler...")
        try:
            # URL format: postgresql://postgres:PASSWORD@db.nnapoohhhibyxlebsxqj.supabase.co:5432/postgres
            part1 = db_url.split("://")[1]
            auth_part = part1.split("@")[0]
            password = auth_part.split(":")[1]
            db_url = f"postgresql://postgres.nnapoohhhibyxlebsxqj:{password}@aws-1-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require"
            print("Successfully mapped to IPv4 pooler connection string.")
        except Exception as e:
            print(f"Warning: Could not parse database URL for pooler mapping: {e}")
        
    migration_file = os.path.join(script_dir, "migrations", "0001_initial_schema.sql")
    if not os.path.exists(migration_file):
        print(f"Error: Migration file not found at {migration_file}")
        sys.exit(1)
        
    print(f"Reading migration file from: {migration_file}")
    with open(migration_file, "r", encoding="utf-8") as f:
        migration_sql = f.read()

    print("Connecting to Supabase Database...")
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = False # Run in transaction
        cursor = conn.cursor()
        
        print("Executing migration SQL...")
        cursor.execute(migration_sql)
        conn.commit()
        print("Migration executed and committed successfully!")
        
        # Verify schema by listing tables and columns
        print("\nVerifying schema in public namespace:")
        query = """
            SELECT table_name, column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            ORDER BY table_name, ordinal_position;
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        
        current_table = None
        for table, column, data_type in rows:
            if table != current_table:
                current_table = table
                print(f"\nTable: {current_table}")
            print(f"  - {column} ({data_type})")
            
        cursor.close()
        conn.close()
        print("\nVerification completed successfully!")
        
    except Exception as e:
        print(f"Error executing migration: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
