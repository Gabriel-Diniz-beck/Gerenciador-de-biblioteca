from flask import Flask, render_template, request, redirect, url_for, session
import json, os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "biblioteca123"  # em produção, use uma variável de ambiente

# ---------------- Funções Auxiliares ----------------
def carregar_arquivo(nome):
    if not os.path.exists(nome):
        with open(nome, "w") as f:
            json.dump([], f)
    with open(nome, "r") as f:
        return json.load(f)

def salvar_arquivo(nome, dados):
    with open(nome, "w") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

# ---------------- Página inicial ----------------
@app.route("/")
def index():
    return render_template("index.html")


# ---------------- Usuário ----------------
@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        usuarios = carregar_arquivo("dados/usuarios.json")

        # checar se usuário já existe
        usuario_novo = request.form["usuario"]
        if any(u["usuario"] == usuario_novo for u in usuarios):
            return "Nome de usuário já existe! Escolha outro.", 400

        novo = {
            "nome": request.form["nome"],
            "usuario": usuario_novo,
            # armazena o hash da senha, não a senha em texto puro
            "senha": generate_password_hash(request.form["senha"])
        }
        usuarios.append(novo)
        salvar_arquivo("dados/usuarios.json", usuarios)
        return redirect(url_for("login_usuario"))
    return render_template("cadastro_usuario.html")


@app.route("/login_usuario", methods=["GET", "POST"])
def login_usuario():
    if request.method == "POST":
        usuarios = carregar_arquivo("dados/usuarios.json")
        usuario = request.form["usuario"]
        senha = request.form["senha"]

        # buscar usuário
        for u in usuarios:
            if u["usuario"] == usuario:
                # verificar hash
                if check_password_hash(u["senha"], senha):
                    # armazenar só os dados necessários na sessão (não a senha)
                    session["usuario"] = {"usuario": u["usuario"], "nome": u["nome"]}
                    return redirect(url_for("usuario_area"))
                else:
                    return "Usuário ou senha inválidos!", 401
        return "Usuário ou senha inválidos!", 401
    return render_template("login_usuario.html")


@app.route("/usuario_area")
def usuario_area():
    if "usuario" not in session:
        return redirect(url_for("login_usuario"))
    return render_template("usuario_area.html", usuario=session["usuario"])


@app.route("/status_usuario")
def status_usuario():
    if "usuario" not in session:
        return redirect(url_for("login_usuario"))
    emprestimos = carregar_arquivo("dados/emprestimos.json")
    meus = [e for e in emprestimos if e["usuario"] == session["usuario"]["usuario"]]
    return render_template("status_usuario.html", emprestimos=meus)


@app.route("/pegar_livro")
def pegar_livro():
    if "usuario" not in session:
        return redirect(url_for("login_usuario"))
    livros = carregar_arquivo("dados/livros.json")
    return render_template("pegar_livro.html", livros=livros)


@app.route("/pegar_livro/<titulo>")
def emprestar_livro(titulo):
    if "usuario" not in session:
        return redirect(url_for("login_usuario"))
    emprestimos = carregar_arquivo("dados/emprestimos.json")
    emprestimos.append({
        "usuario": session["usuario"]["usuario"],
        "titulo": titulo,
        "data": datetime.now().strftime("%d/%m/%Y"),
        "entregue": False
    })
    salvar_arquivo("dados/emprestimos.json", emprestimos)
    return redirect(url_for("status_usuario"))


@app.route("/devolver/<titulo>")
def devolver_livro(titulo):
    if "usuario" not in session:
        return redirect(url_for("login_usuario"))
    emprestimos = carregar_arquivo("dados/emprestimos.json")
    for e in emprestimos:
        if e["titulo"] == titulo and e["usuario"] == session["usuario"]["usuario"]:
            e["entregue"] = True
    salvar_arquivo("dados/emprestimos.json", emprestimos)
    return redirect(url_for("status_usuario"))


@app.route("/logout")
def logout():
    session.pop("usuario", None)
    session.pop("admin", None)
    return redirect(url_for("index"))


# ---------------- Admin ----------------
@app.route("/login_admin", methods=["GET", "POST"])
def login_admin():
    if request.method == "POST":
        usuario = request.form["usuario"]
        senha = request.form["senha"]
        # em produção, não deixe credenciais hardcoded
        if usuario == "admin" and senha == "admin123":
            session["admin"] = True
            return redirect(url_for("admin_area"))
        return "Login de administrador inválido!"
    return render_template("login_admin.html")


@app.route("/admin_area")
def admin_area():
    if "admin" not in session:
        return redirect(url_for("login_admin"))
    return render_template("admin_area.html")


@app.route("/cadastrar", methods=["GET", "POST"])
def cadastrar_livro():
    if "admin" not in session:
        return redirect(url_for("login_admin"))
    if request.method == "POST":
        livros = carregar_arquivo("dados/livros.json")
        livros.append({"titulo": request.form["titulo"], "autor": request.form["autor"]})
        salvar_arquivo("dados/livros.json", livros)
        return redirect(url_for("lista_livro"))
    return render_template("cadastrar_livro.html")


@app.route("/lista_livro")
def lista_livro():
    if "admin" not in session:
        return redirect(url_for("login_admin"))
    livros = carregar_arquivo("dados/livros.json")
    return render_template("lista_livro.html", livros=livros)


@app.route("/remover_livro/<titulo>")
def remover_livro(titulo):
    if "admin" not in session:
        return redirect(url_for("login_admin"))
    livros = carregar_arquivo("dados/livros.json")
    livros = [l for l in livros if l["titulo"] != titulo]
    salvar_arquivo("dados/livros.json", livros)
    return redirect(url_for("lista_livro"))


@app.route("/emprestimos")
def emprestimos():
    if "admin" not in session:
        return redirect(url_for("login_admin"))
    emprestimos = carregar_arquivo("dados/emprestimos.json")
    return render_template("emprestimos.html", emprestimos=emprestimos)


# ---------------- Formulário (Usuário → Admin) ----------------
@app.route("/formulario", methods=["GET", "POST"])
def formulario():
    if request.method == "POST":
        forms = carregar_arquivo("dados/formularios.json")
        forms.append({
            "nome": session["usuario"]["nome"] if "usuario" in session else request.form["nome"],
            "email": request.form["email"],
            "mensagem": request.form["mensagem"],
            "resposta": ""
        })
        salvar_arquivo("dados/formularios.json", forms)
        return "Mensagem enviada!"
    return render_template("formulario.html")


# ---------------- Admin visualiza e responde ----------------
@app.route("/ver_formularios")
def ver_formularios():
    if "admin" not in session:
        return redirect(url_for("login_admin"))
    forms = carregar_arquivo("dados/formularios.json")
    return render_template("formularios_admin.html", formularios=forms)


@app.route("/responder/<int:idx>", methods=["POST"])
def responder(idx):
    if "admin" not in session:
        return redirect(url_for("login_admin"))
    forms = carregar_arquivo("dados/formularios.json")
    resposta = request.form["resposta"]
    forms[idx]["resposta"] = resposta
    salvar_arquivo("dados/formularios.json", forms)
    return redirect(url_for("ver_formularios"))


# ---------------- Usuário visualiza respostas ----------------
@app.route("/minhas_mensagens")
def minhas_mensagens():
    if "usuario" not in session:
        return redirect(url_for("login_usuario"))
    forms = carregar_arquivo("dados/formularios.json")
    minhas = [f for f in forms if f["nome"] == session["usuario"]["nome"]]
    return render_template("minhas_mensagens.html", mensagens=minhas)


# ---------------- Página de erro ----------------
@app.errorhandler(404)
def pagina_nao_encontrada(e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True)

