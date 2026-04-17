#Sistema de Biblioteca Web

Um sistema web para gerenciamento de biblioteca, desenvolvido com **Flask**, permitindo cadastro de livros, alunos e controle de empréstimos — com interface moderna e autocomplete inteligente.

---

##Funcionalidades

##Usuários

* Cadastro e login de usuários
* Diferenciação entre usuário comum e administrador
* Visualização do acervo disponível

##Livros

* Cadastro manual ou automático via API
* Autocomplete inteligente (estilo Netflix 🎬)
* Exibição com capa, autor e descrição
* Edição e remoção de livros

## Alunos

* Cadastro de alunos com matrícula única
* Exclusão de alunos

### Empréstimos

* Registro de empréstimos de livros
* Controle de quantidade disponível
* Devolução de livros

##Autocomplete Inteligente

* Busca automática de livros via:

  * Google Books API
  * OpenLibrary (fallback)
* Preenchimento automático de:

  * Título
  * Autor
  * Capa
  * Descrição

---

##Tecnologias Utilizadas

* Python
* Flask
* Flask-Login
* Flask-SQLAlchemy
* SQLite
* Bootstrap 5
* JavaScript (Vanilla)
* APIs externas:

  * Google Books API
  * OpenLibrary API

---

##Estrutura do Projeto

```
📁 projeto
│
├── app.py
├── biblioteca.db
├── templates/
│   ├── login.html
│   ├── cadastro.html
│   ├── admin.html
│   └── usuario.html

```

---

##Como Rodar o Projeto

### 1. Clone o repositório

```bash
git clone https://github.com/Fl0ppy2030/Automatic-Library-for-schools
cd Automatic-Library-for-schools
```

### 2. Crie um ambiente virtual

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### 3. Instale as dependências

```bash
pip install flask flask_sqlalchemy flask_login requests
```

### 4. Execute o projeto

```bash
python app.py
```

### 5. Acesse no navegador

```
http://localhost:5000
```

---

##Usuário Padrão

Ao iniciar o sistema pela primeira vez, será criado automaticamente:

* **Usuário:** `admin`
* **Senha:** `admin123`

---

##Interface

* Layout moderno com Bootstrap
* Cards interativos de livros
* Modal com visual estilo Netflix 🎬
* Exibição de capa completa do livro
* Responsivo para diferentes dispositivos

---

##Diferenciais

* Autocomplete inteligente com debounce
* Fallback automático entre APIs
* Interface intuitiva e fluida
* Sistema leve e rápido (SQLite)
* Código organizado e fácil de expandir

---

##Melhorias Futuras

* Sistema de favoritos ⭐
* Busca interna no acervo 🔍
* Upload de capas manual 📷
* Controle de prazos de empréstimo ⏳
* Notificações de atraso 📩
* Dark mode 🌙

---

##Autor

Desenvolvido por FL0ppy
