print("1. Loading imports...", flush=True)

from psycopg.conninfo import make_conninfo
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.store.postgres import PostgresStore
from p07_persistentAgents.common import database_url

if __name__ == "__main__":
    print("2. Reading database configuration...", flush=True)

    db_uri = make_conninfo(
        database_url(),
        connect_timeout=10,
        options="-c statement_timeout=30000 -c lock_timeout=10000",
    )

    print("3. Connecting checkpoint saver...", flush=True)
    with PostgresSaver.from_conn_string(db_uri) as saver:
        print("4. Running saver.setup()...", flush=True)
        saver.setup()
        print("5. Saver setup finished; closing connection...", flush=True)

    print("6. Connecting store...", flush=True)
    with PostgresStore.from_conn_string(db_uri) as store:
        print("7. Running store.setup()...", flush=True)
        store.setup()
        print("8. Store setup finished; closing connection...", flush=True)

    print("9. Checkpoint and Store tables are ready.", flush=True)