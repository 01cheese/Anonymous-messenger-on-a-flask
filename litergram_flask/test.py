
with app.app_context():
    db.create_all()  # This ensures the context is active when you create the tables
