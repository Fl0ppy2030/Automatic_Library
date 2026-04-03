from flask import Flask, render_template, request, redirect, flash, abort, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import requests

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///biblioteca.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ---------------- MODELOS ----------------

class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(200))
    is_admin = db.Column(db.Boolean, default=False)

class Livro(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(120))
    autor = db.Column(db.String(120))
    quantidade = db.Column(db.Integer, default=1)
    capa_url = db.Column(db.String(300))
    descricao = db.Column(db.Text)

class Aluno(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    matricula = db.Column(db.String(20), unique=True)

class Emprestimo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    livro_id = db.Column(db.Integer, db.ForeignKey('livro.id'))
    aluno_id = db.Column(db.Integer, db.ForeignKey('aluno.id'))

    livro = db.relationship('Livro')
    aluno = db.relationship('Aluno')

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# ---------------- APIs ----------------

def buscar_capa(titulo):
    try:
        r = requests.get("https://openlibrary.org/search.json", params={"q": titulo}, timeout=5)
        for item in r.json().get("docs", []):
            if item.get("cover_i"):
                return f"https://covers.openlibrary.org/b/id/{item['cover_i']}-L.jpg"
    except:
        pass
    return ""

def buscar_descricao(titulo):
    try:
        r = requests.get(f"https://www.googleapis.com/books/v1/volumes?q={titulo}", timeout=5)
        for item in r.json().get("items", []):
            desc = item.get("volumeInfo", {}).get("description")
            if desc:
                return desc[:400] + "..."
    except:
        pass
    return "Sem descrição."

# ---------------- AUTOCOMPLETE ----------------

@app.route('/buscar_livros')
def buscar_livros():
    q = request.args.get('q', '').strip()

    if not q:
        return jsonify({"livros": []})

    resultados = []

    # -------- GOOGLE --------
    try:
        response = requests.get(
            "https://www.googleapis.com/books/v1/volumes",
            params={"q": q, "maxResults": 5},
            timeout=5
        )

        if response.status_code == 200:
            data = response.json()

            for item in data.get("items", []):
                volume = item.get("volumeInfo", {})

                resultados.append({
                    "titulo": volume.get("title", "Sem título"),
                    "autor": ", ".join(volume.get("authors", [])) if volume.get("authors") else "Autor desconhecido",
                    "capa": volume.get("imageLinks", {}).get("thumbnail", ""),
                    "descricao": (volume.get("description") or "Sem descrição.")[:400] + "..."
                })

        else:
            print("Google bloqueou:", response.status_code)

    except Exception as e:
        print("Erro Google:", e)

    # -------- FALLBACK --------
    if not resultados:
        try:
            r = requests.get("https://openlibrary.org/search.json", params={"q": q}, timeout=5)
            data = r.json()

            for item in data.get("docs", [])[:5]:
                resultados.append({
                    "titulo": item.get("title", "Sem título"),
                    "autor": ", ".join(item.get("author_name", [])) if item.get("author_name") else "Autor desconhecido",
                    "capa": f"https://covers.openlibrary.org/b/id/{item.get('cover_i')}-M.jpg" if item.get("cover_i") else "",
                    "descricao": "Descrição não disponível."
                })

        except Exception as e:
            print("Erro OpenLibrary:", e)

    return jsonify({"livros": resultados})

# ---------------- ROTAS ----------------

@app.route('/')
def home():
    return redirect('/login')

# LOGIN
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        user = Usuario.query.filter_by(username=request.form['username']).first()

        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect('/admin' if user.is_admin else '/meu_acervo')

        flash("Login inválido")

    return render_template('login.html')

# CADASTRO
@app.route('/cadastro', methods=['GET','POST'])
def cadastro():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash("Preencha todos os campos")
            return redirect('/cadastro')

        if Usuario.query.filter_by(username=username).first():
            flash("Usuário já existe")
            return redirect('/cadastro')

        user = Usuario(
            username=username,
            password=generate_password_hash(password)
        )

        aluno = Aluno(nome=username, matricula=username)

        db.session.add(user)
        db.session.add(aluno)
        db.session.commit()

        login_user(user)
        return redirect('/meu_acervo')

    return render_template('cadastro.html')

# LOGOUT
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')

# ---------------- ADMIN ----------------

@app.route('/admin')
@login_required
def admin():
    if not current_user.is_admin:
        abort(403)

    return render_template(
        'admin.html',
        livros=Livro.query.all(),
        alunos=Aluno.query.all(),
        alugados=Emprestimo.query.all()
    )

# ADD LIVRO
@app.route('/add_livro', methods=['POST'])
@login_required
def add_livro():
    if not current_user.is_admin:
        abort(403)

    titulo = request.form.get('titulo')

    if not titulo:
        flash("Título obrigatório")
        return redirect('/admin')

    livro = Livro(
        titulo=titulo,
        autor=request.form.get('autor'),
        quantidade=int(request.form.get('quantidade') or 1),
        capa_url=request.form.get('capa_url') or buscar_capa(titulo),
        descricao=request.form.get('descricao') or buscar_descricao(titulo)
    )

    db.session.add(livro)
    db.session.commit()

    return redirect('/admin')

# EDITAR LIVRO
@app.route('/editar_livro/<int:id>', methods=['POST'])
@login_required
def editar_livro(id):
    livro = Livro.query.get_or_404(id)

    livro.titulo = request.form.get('titulo')
    livro.autor = request.form.get('autor')
    livro.quantidade = int(request.form.get('quantidade') or 1)
    livro.capa_url = request.form.get('capa_url')
    livro.descricao = request.form.get('descricao')

    db.session.commit()

    return redirect('/admin')

# DELETE LIVRO
@app.route('/delete_livro/<int:id>')
@login_required
def delete_livro(id):
    livro = Livro.query.get_or_404(id)

    Emprestimo.query.filter_by(livro_id=id).delete()

    db.session.delete(livro)
    db.session.commit()

    return redirect('/admin')

# ADD ALUNO
@app.route('/add_aluno', methods=['POST'])
@login_required
def add_aluno():
    nome = request.form.get('nome')
    matricula = request.form.get('matricula')

    if not nome or not matricula:
        flash("Preencha tudo")
        return redirect('/admin')

    if Aluno.query.filter_by(matricula=matricula).first():
        flash("Matrícula já existe")
        return redirect('/admin')

    db.session.add(Aluno(nome=nome, matricula=matricula))
    db.session.commit()

    return redirect('/admin')

# DELETE ALUNO
@app.route('/delete_aluno/<int:id>')
@login_required
def delete_aluno(id):
    aluno = Aluno.query.get_or_404(id)

    Emprestimo.query.filter_by(aluno_id=id).delete()

    db.session.delete(aluno)
    db.session.commit()

    return redirect('/admin')

# EMPRESTAR
@app.route('/alugar', methods=['POST'])
@login_required
def alugar():
    livro = Livro.query.get_or_404(request.form['livro_id'])

    if livro.quantidade <= 0:
        flash("Sem estoque")
        return redirect('/admin')

    livro.quantidade -= 1

    db.session.add(Emprestimo(
        livro_id=request.form['livro_id'],
        aluno_id=request.form['aluno_id']
    ))

    db.session.commit()

    return redirect('/admin')

# DEVOLVER
@app.route('/devolver/<int:id>')
@login_required
def devolver(id):
    emp = Emprestimo.query.get_or_404(id)

    emp.livro.quantidade += 1

    db.session.delete(emp)
    db.session.commit()

    return redirect('/admin')

# ---------------- USUARIO ----------------

@app.route('/meu_acervo')
@login_required
def usuario():
    return render_template('usuario.html', livros=Livro.query.all())

# ---------------- START ----------------

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        if not Usuario.query.filter_by(username='admin').first():
            db.session.add(Usuario(
                username='admin',
                password=generate_password_hash('admin123'),
                is_admin=True
            ))
            db.session.commit()

    app.run(debug=True)