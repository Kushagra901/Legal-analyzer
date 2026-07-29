# add_trigger.py
import os

import psycopg2


def load_env(env_path):
    env_vars = {}
    if not os.path.exists(env_path):
        return env_vars
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip("'").strip('"')
                env_vars[key] = val
    return env_vars

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(script_dir, ".env")
    env = load_env(env_path)

    db_url = env.get("DATABASE_URL")
    if not db_url:
        print("Error: DATABASE_URL not found.")
        return

    if "db.nnapoohhhibyxlebsxqj.supabase.co" in db_url:
        part1 = db_url.split("://")[1]
        auth_part = part1.split("@")[0]
        password = auth_part.split(":")[1]
        db_url = f"postgresql://postgres.nnapoohhhibyxlebsxqj:{password}@aws-1-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require"

    sql = """
    CREATE OR REPLACE FUNCTION public.handle_new_user()
    RETURNS trigger AS $$
    BEGIN
      INSERT INTO public.users (id, email, role)
      VALUES (new.id, new.email, 'user')
      ON CONFLICT (id) DO NOTHING;
      RETURN NEW;
    END;
    $$ LANGUAGE plpgsql SECURITY DEFINER;

    DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

    CREATE TRIGGER on_auth_user_created
      AFTER INSERT ON auth.users
      FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
    """

    print("Connecting to database...")
    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        print("Creating handle_new_user trigger...")
        cursor.execute(sql)
        conn.commit()
        cursor.close()
        conn.close()
        print("Trigger successfully created!")
    except Exception as e:
        print(f"Error creating trigger: {e}")

if __name__ == "__main__":
    main()
