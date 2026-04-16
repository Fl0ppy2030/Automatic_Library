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
    username = db.Column(db.String(50), unique=True, nullable=False)  # login
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    aluno_id = db.Column(db.Integer, db.ForeignKey('aluno.id'))
    aluno = db.relationship('Aluno', backref='usuario', uselist=False)

class Livro(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(120), nullable=False)
    autor = db.Column(db.String(120))
    editora = db.Column(db.String(120))
    ano = db.Column(db.String(10))
    categoria = db.Column(db.String(100))
    isbn = db.Column(db.String(20))
    paginas = db.Column(db.Integer)

    quantidade = db.Column(db.Integer, default=1)
    capa_url = db.Column(db.String(300))
    descricao = db.Column(db.Text)

class Aluno(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    matricula = db.Column(db.String(20), unique=True, nullable=False)

class Emprestimo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    livro_id = db.Column(db.Integer, db.ForeignKey('livro.id'))
    aluno_id = db.Column(db.Integer, db.ForeignKey('aluno.id'))

    livro = db.relationship('Livro')
    aluno = db.relationship('Aluno')


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Usuario, int(user_id))


# ---------------- HELPERS ----------------

def normalizar(texto):
    return texto.strip().lower()


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


# ---------------- ROTAS ----------------

@app.route('/')
def home():
    return redirect('/login')


# -------- LOGIN --------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = normalizar(request.form.get('username', ''))
        password = request.form.get('password', '').strip()

        user = Usuario.query.filter_by(username=username).first()

        if not user:
            flash("Usuário não encontrado")
            return redirect('/login')

        if not check_password_hash(user.password, password):
            flash("Senha incorreta")
            return redirect('/login')

        login_user(user)

        if user.is_admin:
            return redirect('/admin')
        else:
            return redirect('/meu_acervo')

    return render_template('login.html')


# -------- CADASTRO --------
@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':

        nome = request.form.get('nome', '').strip()
        matricula = normalizar(request.form.get('matricula', ''))
        password = request.form.get('password', '').strip()
        confirm = request.form.get('confirm_password', '').strip()

        # VALIDAÇÃO
        if not nome or not matricula or not password or not confirm:
            flash("Preencha todos os campos")
            return redirect('/cadastro')

        if password != confirm:
            flash("As senhas não coincidem")
            return redirect('/cadastro')

        if len(password) < 4:
            flash("Senha muito curta (mínimo 4 caracteres)")
            return redirect('/cadastro')

        if Usuario.query.filter_by(username=matricula).first():
            flash("Usuário já existe")
            return redirect('/cadastro')

        try:
            aluno = Aluno(nome=nome, matricula=matricula)
            db.session.add(aluno)
            db.session.flush()

            user = Usuario(
                username=matricula,
                password=generate_password_hash(password),
                aluno_id=aluno.id
            )

            db.session.add(user)
            db.session.commit()

            login_user(user)
            return redirect('/meu_acervo')

        except Exception as e:
            db.session.rollback()
            print("Erro cadastro:", e)
            flash("Erro ao criar conta")
            return redirect('/cadastro')

    return render_template('cadastro.html')


# -------- LOGOUT --------
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')


# -------- ADMIN --------
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


# -------- LIVROS --------
@app.route('/add_livro', methods=['POST'])
@login_required
def add_livro():
    if not current_user.is_admin:
        abort(403)

    livro = Livro(
        titulo=request.form.get('titulo'),
        autor=request.form.get('autor'),
        editora=request.form.get('editora'),
        ano=request.form.get('ano'),
        categoria=request.form.get('categoria'),
        isbn=request.form.get('isbn'),
        paginas=int(request.form.get('paginas') or 0),

        quantidade=int(request.form.get('quantidade') or 1),
        capa_url=request.form.get('capa_url'),
        descricao=request.form.get('descricao')
    )

    db.session.add(livro)
    db.session.commit()

    return redirect('/admin')


@app.route('/editar_livro/<int:id>', methods=['POST'])
@login_required
def editar_livro(id):
    if not current_user.is_admin:
        abort(403)

    livro = Livro.query.get_or_404(id)

    livro.titulo = request.form.get('titulo', '').strip()
    livro.autor = request.form.get('autor', '').strip()
    livro.quantidade = int(request.form.get('quantidade') or 1)
    livro.capa_url = request.form.get('capa_url', '')
    livro.descricao = request.form.get('descricao', '')

    db.session.commit()
    return redirect('/admin')


@app.route('/delete_livro/<int:id>')
@login_required
def delete_livro(id):
    if not current_user.is_admin:
        abort(403)

    livro = Livro.query.get_or_404(id)

    Emprestimo.query.filter_by(livro_id=id).delete()

    db.session.delete(livro)
    db.session.commit()

    return redirect('/admin')


# -------- ALUNOS --------
@app.route('/add_aluno', methods=['POST'])
@login_required
def add_aluno():
    if not current_user.is_admin:
        abort(403)

    nome = request.form.get('nome', '').strip()
    matricula = request.form.get('matricula', '').strip()
    senha = request.form.get('senha', '').strip()

    # VALIDAÇÃO
    if not nome or not matricula or not senha:
        flash("Preencha todos os campos")
        return redirect('/admin')

    # DUPLICADO
    if Usuario.query.filter_by(username=matricula).first():
        flash("Aluno já existe")
        return redirect('/admin')

    try:
        aluno = Aluno(nome=nome, matricula=matricula)
        db.session.add(aluno)
        db.session.flush()

        user = Usuario(
            username=matricula,
            password=generate_password_hash(senha),
            aluno_id=aluno.id
        )

        db.session.add(user)
        db.session.commit()

        flash("Aluno criado com sucesso")

    except Exception as e:
        db.session.rollback()
        print(e)
        flash("Erro ao criar aluno")

    return redirect('/admin')


@app.route('/delete_aluno/<int:id>')
@login_required
def delete_aluno(id):
    if not current_user.is_admin:
        abort(403)

    aluno = Aluno.query.get_or_404(id)

    Emprestimo.query.filter_by(aluno_id=id).delete()

    db.session.delete(aluno)
    db.session.commit()

    return redirect('/admin')


# -------- EMPRÉSTIMOS --------
@app.route('/alugar', methods=['POST'])
@login_required
def alugar():
    if not current_user.is_admin:
        abort(403)

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


@app.route('/devolver/<int:id>')
@login_required
def devolver(id):
    if not current_user.is_admin:
        abort(403)

    emp = Emprestimo.query.get_or_404(id)

    emp.livro.quantidade += 1

    db.session.delete(emp)
    db.session.commit()

    return redirect('/admin')


# -------- API BUSCA --------
@app.route('/buscar_livros')
def buscar_livros():
    q = request.args.get('q', '').strip()

    if not q:
        return jsonify({"livros": []})

    resultados = []

    try:
        r = requests.get(
            "https://www.googleapis.com/books/v1/volumes",
            params={"q": q, "maxResults": 5},
            timeout=5
        )

        data = r.json()

        for item in data.get("items", []):
            v = item.get("volumeInfo", {})

            resultados.append({
                "titulo": v.get("title", ""),
                "autor": ", ".join(v.get("authors", [])) if v.get("authors") else "",
                "editora": v.get("publisher", ""),
                "ano": v.get("publishedDate", "")[:4],
                "categoria": ", ".join(v.get("categories", [])) if v.get("categories") else "",
                "isbn": next(
                    (i["identifier"] for i in v.get("industryIdentifiers", []) if i["type"] == "ISBN_13"),
                    ""
                ),
                "paginas": v.get("pageCount", ""),
                "capa": v.get("imageLinks", {}).get("thumbnail", ""),
                "descricao": (v.get("description") or "")[:300]
            })

    except Exception as e:
        print("ERRO GOOGLE:", e)

    if not resultados:
        try:
            r = requests.get("https://openlibrary.org/search.json", params={"q": q}, timeout=5)
            data = r.json()

            for item in data.get("docs", [])[:5]:
                resultados.append({
                    "titulo": item.get("title", ""),
                    "autor": ", ".join(item.get("author_name", [])) if item.get("author_name") else "",
                    "editora": "",
                    "ano": "",
                    "categoria": "",
                    "isbn": "",
                    "paginas": "",
                    "capa": f"https://covers.openlibrary.org/b/id/{item.get('cover_i')}-M.jpg" if item.get("cover_i") else "",
                    "descricao": ""
                })

        except Exception as e:
            print("ERRO OPENLIB:", e)

    return jsonify({"livros": resultados})


# -------- USUÁRIO --------
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
