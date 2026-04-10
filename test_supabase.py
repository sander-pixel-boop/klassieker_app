from supabase import create_client
try:
    url = "https://example.supabase.co"
    key = "fake-key"
    client = create_client(url, key)
    res = client.table("gebruikers_data_test").select("password").eq("username", "test").execute()
    print("Success")
except Exception as e:
    print(f"Exception: {e}")
    print(type(e))
