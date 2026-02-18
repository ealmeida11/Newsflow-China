# Subir o projeto no GitHub

## 1. Criar o repositório no GitHub

1. Acesse https://github.com/new
2. **Repository name:** por exemplo `Newsflow-China` ou `china-news`
3. Deixe **Private** ou **Public**, como preferir
4. **Não** marque "Add a README" (já temos um)
5. Clique em **Create repository**

## 2. Conectar e enviar o código

No terminal, na pasta do projeto (`News`), rode (troque `SEU_USUARIO` e `NOME_DO_REPO` pelo seu usuário GitHub e nome do repositório):

```powershell
cd "r:\Economics\Ealmeida\China\News"

git remote add origin https://github.com/SEU_USUARIO/NOME_DO_REPO.git
git branch -M main
git push -u origin main
```

Exemplo se o repositório for `github.com/ealmeida/Newsflow-China`:

```powershell
git remote add origin https://github.com/ealmeida/Newsflow-China.git
git branch -M main
git push -u origin main
```

Se o GitHub pedir autenticação, use um **Personal Access Token** (Settings → Developer settings → Personal access tokens) no lugar da senha, ou configure o Git Credential Manager.
