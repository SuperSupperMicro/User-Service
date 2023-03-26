import os
import pytest
from userservice import create_app

@pytest.fixture
def app():

    app = create_app({
        'TESTING': True,
        'DATABASE': db_path
    })

    with app.app_context():
        con, cur = test_db_connect()
        cur.exeute('{Call ResetTestDB}')
        test_db_close(con, cur)

    yield app


@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()

def test_db_connect():
    server = os.environ.get('MSSQL_TEST_SERVER')
    database = os.environ.get('MSSQL_TEST_DB')
    username = os.environ.get('MSSQL_TEST_USERNAME')
    password = os.environ.get('MSSQL_TEST_PASSWORD')

    try:
        con = db.connect(
            'DRIVER={ODBC Driver 17 for SQL Server};SERVER=%s;DATABASE=%s;UID=%s;PWD=%s;TrustServerCertificate=yes'
            % (server, database, username, password)
        )
        cur = g.con.cursor()

        return con, cur

    except ValueError as e:
        print(e)
        return f"Error {e}"

def test_db_close(connection, cursor):
    # commits all sql statements on this connection
    cursor.commit()
    # close & delete cursor
    cursor.close()
    del cursor
    # close connection
    connection.close()