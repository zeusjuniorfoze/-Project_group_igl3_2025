from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
    app.config['PROPAGATE_EXCEPTIONS'] = True
    app.config['DEBUG'] = True
    app.config['SQLALCHEMY_ECHO'] = True  # déjà activé, on garde

