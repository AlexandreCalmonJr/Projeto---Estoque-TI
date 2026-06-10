# 📦 Almoxarifado Digital — Sistema de Gestão de Estoque e Patrimônio

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.3.3-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Sistema completo e profissional para gerenciamento de estoque e patrimônio, desenvolvido com Flask e SQLite/PostgreSQL. Ideal para empresas que precisam controlar equipamentos, consumíveis e ativos patrimoniais em múltiplas unidades.

![Sistema de Gestão de Ativos](https://via.placeholder.com/800x400/3B82F6/FFFFFF?text=Sistema+de+Gestão+de+Ativos+de+TI)

## 📋 Índice

- [Características Principais](#-características-principais)
- [Tecnologias Utilizadas](#-tecnologias-utilizadas)
- [Requisitos do Sistema](#-requisitos-do-sistema)
- [Instalação](#-instalação)
- [Configuração](#-configuração)
- [Uso do Sistema](#-uso-do-sistema)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Funcionalidades Detalhadas](#-funcionalidades-detalhadas)
- [Geração de Executável](#-geração-de-executável)
- [API e Endpoints](#-api-e-endpoints)
- [Segurança](#-segurança)
- [Solução de Problemas](#-solução-de-problemas)
- [Contribuindo](#-contribuindo)
- [Roadmap](#-roadmap)
- [Licença](#-licença)
- [Contato](#-contato)

---

## 🎯 Características Principais

### ✨ Gerenciamento Completo de Ativos
- **Cadastro Detalhado**: Registre ativos com patrimônio, número de série, marca, modelo, especificações técnicas (CPU, RAM, armazenamento, SO)
- **Múltiplas Categorias**: Desktop, Notebook, Servidor, Roteador, Switch, Impressora, Monitor e muito mais
- **Rastreamento de Status**: Em Estoque, Em Uso, Em Manutenção, Descartado
- **Histórico Completo**: Cada movimentação é registrada com timestamp e detalhes

### 👥 Controle de Usuários e Permissões
- **Sistema de Login**: Autenticação segura com hash de senhas (Werkzeug)
- **Dois Níveis de Acesso**: Administradores e Usuários Básicos
- **Painel Administrativo**: Gestão completa de usuários e estatísticas consolidadas

### 🗄️ Suporte a Múltiplas Bases de Dados
- **Multi-Database**: Gerencie ativos de diferentes localidades em bases separadas
- **Bases Configuráveis**: Salvador, Minas Gerais, Sergipe, ou adicione novas facilmente
- **SQLite ou PostgreSQL**: Escolha o banco de dados ideal para seu cenário

### 📊 Dashboard Inteligente
- **KPIs em Tempo Real**: Total de ativos, quantidade em estoque, em uso, em manutenção
- **Gráficos Interativos**: Visualização por status e destino (Chart.js)
- **Filtros Avançados**: Busca por categoria, modelo, texto livre
- **Alertas**: Notificação de ativos com serial provisório

### 📄 Geração de Documentos
- **Termos Automáticos**: Geração de Termos de Responsabilidade, Entrega e Comodato
- **Preenchimento Dinâmico**: Templates .docx com substituição de variáveis
- **Gerador Avulso**: Interface para criar termos sem vincular a ativos específicos

### 📥 Importação em Massa
- **CSV e Excel**: Importe centenas de ativos de uma só vez
- **Criação Automática**: Categorias e modelos são criados automaticamente se não existirem
- **Números de Série Provisórios**: Sistema gera seriais temporários quando não fornecidos
- **Edição em Lote**: Interface para atualizar múltiplos ativos provisórios

### 🔧 Funcionalidades Avançadas
- **Distribuição de Ativos**: Atribua equipamentos a usuários com geração automática de termo
- **Movimentação**: Altere status, envie para manutenção, devolva ao estoque
- **Baixa de Ativos**: Descarte equipamentos com registro de chamado
- **Relatórios Imprimíveis**: Gere relatórios filtrados prontos para impressão ou PDF

---

## 🛠️ Tecnologias Utilizadas

### Backend
- **Python 3.8+**: Linguagem principal
- **Flask 2.3.3**: Framework web
- **Flask-SQLAlchemy 3.0.5**: ORM para banco de dados
- **Flask-Login 0.6.3**: Gerenciamento de sessões
- **Werkzeug 2.3.7**: Utilitários WSGI e hash de senhas

### Frontend
- **Tailwind CSS**: Framework CSS utility-first
- **Chart.js**: Biblioteca de gráficos interativos
- **HTML5/CSS3**: Estrutura e estilização
- **JavaScript ES6+**: Interatividade

### Banco de Dados
- **SQLite**: Banco padrão (desenvolvimento e produção leve)
- **PostgreSQL**: Suporte para ambientes corporativos

### Outras Bibliotecas
- **Pandas**: Manipulação de dados para importação
- **OpenPyXL**: Leitura de arquivos Excel
- **python-docx**: Geração de documentos Word
- **Waitress**: Servidor WSGI de produção
- **PyInstaller**: Geração de executável standalone

---

## 💻 Requisitos do Sistema

### Requisitos Mínimos
- **Sistema Operacional**: Windows 7/10/11, Linux (Ubuntu 18.04+), macOS 10.14+
- **Python**: Versão 3.8 ou superior
- **Memória RAM**: 2 GB
- **Espaço em Disco**: 500 MB (mais espaço para banco de dados)
- **Navegador**: Chrome 90+, Firefox 88+, Edge 90+

### Requisitos Recomendados
- **Memória RAM**: 4 GB ou superior
- **Processador**: Dual-core 2.0 GHz ou superior
- **Espaço em Disco**: 2 GB
- **Resolução de Tela**: 1920x1080 ou superior

---

## 📦 Instalação

### Método 1: Instalação via Python (Recomendado para Desenvolvimento)

#### 1. Clone o Repositório
```bash
git clone https://github.com/seu-usuario/gestao-ativos-ti.git
cd gestao-ativos-ti
```

#### 2. Crie um Ambiente Virtual
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

#### 3. Instale as Dependências
```bash
pip install -r requirements.txt
```

#### 4. Configure o Ambiente
```bash
# Opcional: Defina variáveis de ambiente
# Windows
set FLASK_CONFIG=development

# Linux/macOS
export FLASK_CONFIG=development
```

#### 5. Execute a Aplicação
```bash
python run.py
```

A aplicação abrirá automaticamente no navegador em `http://127.0.0.1:8000`

### Método 2: Executável Standalone (Produção)

Se você recebeu o arquivo `AlmoxarifadoDigital.exe`:

1. Extraia o arquivo para uma pasta
2. Execute `AlmoxarifadoDigital.exe`
3. O sistema abrirá automaticamente no navegador

**Nota**: No Windows, pode aparecer um aviso do SmartScreen. Clique em "Mais informações" e depois "Executar assim mesmo".

---

## ⚙️ Configuração

### Configuração de Banco de Dados

O arquivo `config.py` contém todas as configurações do sistema:

```python
# Banco de dados de autenticação (usuários)
SQLALCHEMY_DATABASE_URI = 'sqlite:///common.db'

# Bancos de dados de ativos (múltiplas localidades)
ASSET_DATABASES = {
    'salvador': {
        'name': 'Salvador (BA)',
        'url': 'sqlite:///salvador_assets.db'
    },
    'minas': {
        'name': 'Minas Gerais (MG)',
        'url': 'sqlite:///minas_assets.db'
    },
    'sergipe': {
        'name': 'Sergipe (SE)',
        'url': 'sqlite:///sergipe_assets.db'
    }
}
```

### Adicionar Nova Base de Dados

Para adicionar uma nova localidade:

1. Edite `config.py`
2. Adicione um novo item ao dicionário `ASSET_DATABASES`:

```python
'nova_localidade': {
    'name': 'Nome Exibido',
    'url': 'sqlite:///nova_localidade_assets.db'
}
```

3. Reinicie a aplicação

### Usar PostgreSQL

Para ambientes corporativos, edite a URL do banco:

```python
'production_db': {
    'name': 'Produção',
    'url': 'postgresql://usuario:senha@host:porta/nome_banco'
}
```

### Usuário Administrador Padrão

Na primeira execução, o sistema cria automaticamente:
- **Usuário**: `admin`
- **Senha**: `admin`

⚠️ **IMPORTANTE**: Altere essas credenciais imediatamente após o primeiro login!

### Criar Novos Usuários via Script

Execute o script `create_user.py`:

```bash
python create_user.py
```

Siga as instruções interativas para criar novos usuários.

---

## 📱 Uso do Sistema

### 1. Login
1. Acesse o sistema
2. Insira suas credenciais
3. Selecione a base de dados desejada
4. Clique em "Entrar"

### 2. Dashboard
- Visualize KPIs e gráficos
- Use filtros para refinar a busca
- Clique em um ativo para ver detalhes

### 3. Cadastrar Ativos

#### Cadastro Individual
1. Menu → **Cadastrar Ativo**
2. Preencha os campos:
   - **Categoria**: Selecione o tipo de equipamento
   - **Modelo**: Escolha ou adicione novo modelo
   - **Marca**: Fabricante do equipamento
   - **Nº de Série**: Identificação única do equipamento
   - **Especificações Técnicas**: CPU, RAM, Armazenamento, SO (opcional)
3. Clique em **Cadastrar Ativo**

**Dica**: Deixe o campo "Patrimônio" em branco para geração automática no formato: `TIPO-ANO-SEQUENCIAL` (ex: `NB-2025-001`)

#### Importação em Massa
1. Menu → **Importar Ativos**
2. Prepare um arquivo CSV ou Excel com as colunas:
   - `ativo` ou `categoria` (obrigatório)
   - `fabricante` ou `marca` (obrigatório)
   - `modelo` (obrigatório)
   - `nº serie` ou `numero_serie` (opcional)
   - `quantidade` (opcional, padrão: 1)
3. Faça upload do arquivo
4. Se houver erros, o sistema informará quais linhas falharam

### 4. Distribuir Ativos
1. Acesse os **Detalhes** do ativo
2. Seção **Distribuir para Usuário**:
   - Preencha: Nome, Email, Unidade, Localidade, Setor, Nº do Chamado
   - Selecione o template de documento
3. Clique em **Distribuir e Gerar Documento**
4. O sistema muda o status para "Em Uso" e baixa o termo automaticamente

### 5. Movimentar Ativos
1. Acesse os **Detalhes** do ativo
2. Seção **Movimentar Ativo**:
   - Selecione o novo status
   - Informe o nº do chamado
3. Clique em **Movimentar**

### 6. Manutenção
- Menu → **Manutenção**: Lista todos os ativos em manutenção
- Visualize quando cada equipamento foi enviado para reparo

### 7. Relatórios
1. Menu → **Relatórios**
2. Aplique filtros se necessário
3. Clique em **Imprimir Relatório** para gerar PDF
4. Clique em linhas da tabela para ver detalhes do ativo

### 8. Editar em Lote
1. Menu → **Editar Ativos em Lote**
2. Visualize ativos com serial provisório
3. Atualize Patrimônio e Nº de Série
4. Salve todas as alterações de uma vez

### 9. Painel Administrativo (Apenas Admins)
1. Menu → **Painel do Admin**
2. **Visão Geral**: Estatísticas consolidadas de todas as bases
3. **Usuários**: Criar, editar, excluir usuários
   - Defina se o usuário é administrador
   - Altere senhas

---

## 📁 Estrutura do Projeto

```
gestao-ativos-ti/
├── app/
│   ├── __init__.py              # Inicialização do Flask
│   ├── models.py                # Modelos de dados (User, AssetManager)
│   ├── database.py              # Funções de banco de dados (PostgreSQL)
│   ├── sqlite_setup.py          # Setup específico para SQLite
│   ├── main/
│   │   ├── __init__.py          # Blueprint principal
│   │   └── routes.py            # Rotas da aplicação
│   ├── admin/
│   │   ├── __init__.py          # Blueprint admin
│   │   └── routes.py            # Rotas administrativas
│   ├── templates/
│   │   ├── base.html            # Template base
│   │   ├── login.html           # Tela de login
│   │   ├── index.html           # Dashboard
│   │   ├── form_ativo.html      # Formulário de cadastro
│   │   ├── detalhes_ativo.html  # Página de detalhes
│   │   ├── edit_ativo.html      # Edição de ativo
│   │   ├── bulk_edit.html       # Edição em lote
│   │   ├── manutencao.html      # Lista de manutenção
│   │   ├── relatorio_geral.html # Relatórios
│   │   ├── importar.html        # Importação
│   │   ├── gerenciar_tipos.html # Gerenciar categorias/modelos
│   │   ├── gerador_termo.html   # Gerador de termo avulso
│   │   ├── _filtros.html        # Componente de filtros
│   │   └── admin/
│   │       ├── base_admin.html  # Template admin
│   │       ├── dashboard.html   # Dashboard admin
│   │       ├── users.html       # Lista de usuários
│   │       └── user_form.html   # Formulário de usuário
│   ├── static/
│   │   └── images/
│   │       └── logo.png         # Logo da empresa
│   └── document_templates/      # Templates de documentos .docx
│       ├── Termo de Entrega de Ativos - modelo.docx
│       ├── Termo de Responsabilidade de Ativos - modelo.docx
│       └── Termo de Comodato - Notebook - modelo.docx
├── config.py                    # Configurações do sistema
├── run.py                       # Script de execução
├── create_user.py               # Script para criar usuários
├── requirements.txt             # Dependências Python
├── EstoqueFacil.spec              # Especificações PyInstaller (gera AlmoxarifadoDigital.exe)
├── README.md                    # Este arquivo
└── LICENSE                      # Licença do projeto
```

---

## 🚀 Funcionalidades Detalhadas

### Sistema de Templates de Documentos

Os templates .docx usam variáveis que são substituídas automaticamente:

| Variável | Descrição |
|----------|-----------|
| `{{solicitante}}` | Nome do solicitante |
| `{{usuario}}` | Email/nome do usuário final |
| `{{matricula}}` | Matrícula do funcionário |
| `{{setor}}` | Setor/departamento |
| `{{unidade}}` | Unidade/local de trabalho |
| `{{localidade}}` | Cidade/estado |
| `{{patrimonio}}` | Número de patrimônio do ativo |
| `{{categoria}}` | Categoria do ativo |
| `{{fabricante}}` | Marca/fabricante |
| `{{modelo}}` | Modelo do equipamento |
| `{{serie}}` | Número de série |
| `{{chamado}}` | Número do chamado/ticket |
| `{{data_hoje}}` | Data atual formatada |

### Geração Automática de IDs

Quando o patrimônio não é informado, o sistema gera automaticamente:

- **Formato**: `SIGLA-ANO-SEQUENCIAL`
- **Exemplo**: `NB-2025-042` (Notebook do ano 2025, 42º registrado)
- **Siglas**: Primeiras 2 letras da categoria (Desktop → DE, Notebook → NB, etc.)

### Números de Série Provisórios

Durante importação em massa sem serial:

- **Formato**: `PROV-TIMESTAMP`
- **Exemplo**: `PROV-1736524800123`
- **Edição**: Use "Editar Ativos em Lote" para atualizar

### Histórico de Movimentações

Cada ação gera um registro automático:

- **Criação**: Ativo cadastrado
- **Distribuição**: Atribuído a usuário
- **Movimentação**: Mudança de status
- **Atualização**: Dados modificados
- **Baixa**: Descarte do equipamento

---

## 🔨 Geração de Executável

### Windows

1. Instale o PyInstaller:
```bash
pip install pyinstaller
```

2. Execute o comando de build:
```bash
pyinstaller EstoqueFacil.spec
```

3. O executável estará em `dist/AlmoxarifadoDigital.exe`

### Distribuição

Para distribuir o executável:

1. Copie a pasta `dist/` completa
2. Inclua a pasta `app/document_templates/` na mesma pasta do .exe
3. Os arquivos de banco de dados (.db) serão criados automaticamente

---

## 🔌 API e Endpoints

### Rotas Principais (Blueprint: main)

| Rota | Método | Descrição | Autenticação |
|------|--------|-----------|--------------|
| `/` | GET | Dashboard principal | Requerida |
| `/login` | GET, POST | Tela de login | Pública |
| `/logout` | GET | Logout do usuário | Requerida |
| `/ativo/novo` | GET, POST | Cadastrar novo ativo | Requerida |
| `/ativo/<id>` | GET | Detalhes do ativo | Requerida |
| `/ativo/<id>/edit` | GET, POST | Editar ativo | Requerida |
| `/ativo/<id>/distribuir` | POST | Distribuir ativo | Requerida |
| `/ativo/<id>/movimentar` | POST | Movimentar ativo | Requerida |
| `/ativo/<id>/baixar` | POST | Dar baixa no ativo | Requerida |
| `/ativo/<id>/gerar_documento/<template>` | GET | Gerar documento | Requerida |
| `/importar` | GET, POST | Importar ativos | Requerida |
| `/bulk-edit` | GET, POST | Editar em lote | Requerida |
| `/manutencao` | GET | Lista de manutenção | Requerida |
| `/relatorios` | GET | Relatórios | Requerida |
| `/gerenciar` | GET, POST | Gerenciar tipos | Requerida |
| `/gerar-termo` | GET | Gerador de termo | Requerida |

### Rotas Administrativas (Blueprint: admin)

| Rota | Método | Descrição | Permissão |
|------|--------|-----------|-----------|
| `/admin/` | GET | Dashboard admin | Admin |
| `/admin/users` | GET | Listar usuários | Admin |
| `/admin/users/new` | GET, POST | Criar usuário | Admin |
| `/admin/users/edit/<id>` | GET, POST | Editar usuário | Admin |
| `/admin/users/delete/<id>` | POST | Deletar usuário | Admin |

---

## 🔒 Segurança

### Autenticação
- Senhas hasheadas com Werkzeug (PBKDF2 + SHA-256)
- Sessões gerenciadas por Flask-Login
- Proteção contra CSRF em formulários

### Autorização
- Decorator `@login_required` protege rotas
- Decorator `@admin_required` para rotas administrativas
- Usuários não podem deletar a si mesmos

### Validações
- Unicidade de patrimônio e número de série
- Validação de entrada em todos os formulários
- Sanitização de dados importados

### Boas Práticas
- **Altere a SECRET_KEY** em produção
- Use HTTPS em ambientes de produção
- Faça backup regular dos bancos de dados
- Mantenha as dependências atualizadas

---

## 🐛 Solução de Problemas

### Problema: "Nenhuma chave de banco de dados encontrada na sessão"

**Causa**: Sessão expirada ou não selecionou base de dados no login

**Solução**: Faça logout e login novamente, selecionando a base

### Problema: Erro ao importar arquivo CSV

**Causa**: Codificação incorreta (comum em arquivos do Excel)

**Solução**: O sistema tenta UTF-8 e Latin-1 automaticamente. Se persistir, salve o CSV com codificação UTF-8

### Problema: "Patrimônio/Serial já existe"

**Causa**: Tentativa de cadastrar ativo com ID duplicado

**Solução**: 
- Verifique se o ativo já está cadastrado
- Use busca no dashboard para localizar
- Para importação, use edição em lote para corrigir provisórios

### Problema: Executável não abre no Windows

**Causa**: Antivírus bloqueando ou falta de dependências

**Solução**:
1. Adicione exceção no antivírus
2. Execute como administrador
3. Verifique se o arquivo não está corrompido

### Problema: Banco de dados travado (SQLite)

**Causa**: Múltiplos acessos simultâneos

**Solução**: 
- Feche todas as instâncias da aplicação
- Delete o arquivo `.db-journal` se existir
- Considere migrar para PostgreSQL

### Problema: Templates de documento não encontrados

**Causa**: Pasta `document_templates` não está no local correto

**Solução**: Certifique-se de que `app/document_templates/` existe e contém os arquivos .docx

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Para contribuir:

1. **Fork** o projeto
2. Crie uma **branch** para sua feature (`git checkout -b feature/MinhaFeature`)
3. **Commit** suas mudanças (`git commit -m 'Adiciona MinhaFeature'`)
4. **Push** para a branch (`git push origin feature/MinhaFeature`)
5. Abra um **Pull Request**

### Diretrizes
- Siga o estilo de código existente (PEP 8 para Python)
- Adicione testes para novas funcionalidades
- Atualize a documentação quando necessário
- Comente código complexo

---

## 🗺️ Roadmap

### Versão 2.0 (Planejado)
- [ ] API RESTful para integração com outros sistemas
- [ ] Relatórios avançados com exportação em Excel
- [ ] Sistema de notificações por email
- [ ] Controle de garantias e prazos de manutenção
- [ ] Dashboard com métricas de custo
- [ ] Aplicativo mobile (React Native)

### Versão 2.5 (Futuro)
- [ ] Integração com sistemas de chamados (ServiceNow, GLPI)
- [ ] QR Code para cada ativo
- [ ] Reconhecimento de imagens (IA para identificar modelos)
- [ ] Relatórios de depreciação
- [ ] Multi-idioma (EN, ES)

---

## 📄 Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

```
MIT License

Copyright (c) 2025 Alexandre Calmon - TI Bahia

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 📧 Contato

**Desenvolvedor**: Alexandre Calmon - TI Bahia

- **Email**: alexandrecalmonjunior@gmail.com
- **GitHub**: [@alexandrecalmon](https://github.com/AlexandreCalmonJr)
- **LinkedIn**: [Alexandre Calmon](https://linkedin.com/in/alexandre-calmon-54ab7016a)

### Suporte
Para reportar bugs ou solicitar features, abra uma [Issue no GitHub](https://github.com/seu-usuario/gestao-ativos-ti/issues).

---

## 🙏 Agradecimentos

- **Flask**: Framework web Python
- **Tailwind CSS**: Framework CSS moderno
- **Chart.js**: Biblioteca de gráficos
- **Comunidade Python**: Pelo suporte contínuo

---
<div align="center">

**⭐ Se este projeto foi útil para você, considere dar uma estrela no GitHub! ⭐**

[![GitHub stars](https://img.shields.io/github/stars/seu-usuario/gestao-ativos-ti?style=social)](https://github.com/seu-usuario/gestao-ativos-ti)

</div>

---

**Desenvolvido  por Alexandre Calmon *
