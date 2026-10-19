import os
from contextlib import closing

import psycopg2
from psycopg2 import errors
from flask import Flask, jsonify, request

app = Flask(__name__)
_table_ready = False


def get_conn():
    """Open a DB connection; create the table the first time we succeed."""
    global _table_ready
    conn = psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        connect_timeout=3,
    )
    if not _table_ready:
        with conn, conn.cursor() as cur:
            cur.execute(
                "CREATE TABLE IF NOT EXISTS users ("
                "id SERIAL PRIMARY KEY, "
                "name TEXT NOT NULL, "
                "email TEXT NOT NULL UNIQUE)"
            )
        _table_ready = True
    return conn


def run(sql, params=(), fetch="none"):
    with closing(get_conn()) as conn:
        with conn:  # commits on success, rolls back on error
            with conn.cursor() as cur:
                cur.execute(sql, params)
                if fetch == "all":
                    return cur.fetchall()
                if fetch == "one":
                    return cur.fetchone()
                return cur.rowcount


def to_user(r):
    return {"id": r[0], "name": r[1], "email": r[2]}


@app.get("/healthz")
def healthz():
    return jsonify(status="ok"), 200


@app.get("/ready")
def ready():
    try:
        run("SELECT 1", fetch="one")
        return jsonify(status="ready"), 200
    except Exception:
        return jsonify(status="database unreachable"), 503


@app.get("/users")
def list_users():
    rows = run("SELECT id, name, email FROM users ORDER BY id", fetch="all")
    return jsonify([to_user(r) for r in rows])


@app.post("/users")
def create_user():
    data = request.get_json(silent=True) or {}
    name, email = data.get("name"), data.get("email")
    if not name or not email:
        return jsonify(error="name and email are required"), 400
    try:
        r = run(
            "INSERT INTO users (name, email) VALUES (%s, %s) RETURNING id, name, email",
            (name, email), fetch="one",
        )
    except errors.UniqueViolation:
        return jsonify(error="email already exists"), 409
    return jsonify(to_user(r)), 201


@app.get("/users/<int:uid>")
def get_user(uid):
    r = run("SELECT id, name, email FROM users WHERE id = %s", (uid,), fetch="one")
    if r is None:
        return jsonify(error="not found"), 404
    return jsonify(to_user(r))


@app.put("/users/<int:uid>")
def update_user(uid):
    data = request.get_json(silent=True) or {}
    name, email = data.get("name"), data.get("email")
    if not name or not email:
        return jsonify(error="name and email are required"), 400
    try:
        r = run(
            "UPDATE users SET name = %s, email = %s WHERE id = %s RETURNING id, name, email",
            (name, email, uid), fetch="one",
        )
    except errors.UniqueViolation:
        return jsonify(error="email already exists"), 409
    if r is None:
        return jsonify(error="not found"), 404
    return jsonify(to_user(r))


@app.delete("/users/<int:uid>")
def delete_user(uid):
    count = run("DELETE FROM users WHERE id = %s", (uid,))
    if count == 0:
        return jsonify(error="not found"), 404
    return "", 204