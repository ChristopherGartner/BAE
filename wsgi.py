from main import BAE


def build(dbhost, dbschema, dbuser, dbpw):
    b = BAE(dbhost, dbuser, dbpw, dbschema)
    return b.create_app()
