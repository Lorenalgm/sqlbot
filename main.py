from flask import Flask, request, jsonify, Response
import subprocess
import threading
import requests
import os

app = Flask(__name__)

# Variável de ambiente para o token do Slack
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")

# Headers para chamadas da API do Slack
HEADERS = {
    "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
    "Content-Type": "application/json"
}

# Traduções específicas para mensagens relacionadas a UPDATE ou DELETE no PostgreSQL
TRANSLATIONS = {
    "L016": "Use sempre uma cláusula WHERE ao fazer UPDATE ou DELETE para evitar alterações em massa.",
    "L019": "Faltando um espaço após a vírgula na cláusula SET.",
    "L040": "As colunas na cláusula SET ou WHERE não estão corretamente separadas por vírgulas.",
    "L042": "Faltando uma palavra-chave explícita como WHERE ou RETURNING após o comando UPDATE ou DELETE.",
    "L044": "Evite usar tabelas sem alias em consultas complexas com UPDATE ou DELETE.",
    "L027": "Os operadores na cláusula SET ou WHERE devem ter um espaço antes e depois (e.g., =).",
    "ambiguous.where_clause": "Cláusula WHERE ausente ou ambígua. Certifique-se de filtrar os resultados corretamente ao usar UPDATE ou DELETE.",
    "ambiguous.column_count": "O comando UPDATE ou DELETE parece estar incompleto ou mal definido.",
    "L031": "Certifique-se de que índices estão sendo usados corretamente ao filtrar em WHERE ou ao usar JOIN."
}

def process_query(query, channel_id, response_url, thread_ts):
    """Processa a query em segundo plano, corrige e envia a resposta ao Slack na thread."""
    try:
        # Salva a query original em um arquivo temporário
        with open("temp.sql", "w") as f:
            f.write(query)

        # Valida a query com SQLFluff
        lint_result = subprocess.run(
            ["sqlfluff", "lint", "--dialect", "postgres", "temp.sql"],
            capture_output=True,
            text=True
        )

        # Corrige a query com SQLFluff
        fix_result = subprocess.run(
            ["sqlfluff", "fix", "--dialect", "postgres", "--force", "temp.sql"],
            capture_output=True,
            text=True
        )

        # Lê a query corrigida
        with open("temp.sql", "r") as f:
            fixed_query = f.read()

        # Processa a saída do SQLFluff lint
        lint_output = lint_result.stdout.strip()
        if not lint_output:
            response_text = f"✅ Nenhum problema encontrado na query! Aqui está sua versão corrigida:\n```\n{fixed_query}\n```"
        else:
            # Formata a saída do SQLFluff lint
            formatted_messages = []
            for line in lint_output.splitlines():
                if "L:" in line and "|" in line:
                    parts = line.split("|")
                    code = parts[-1].strip()
                    message = TRANSLATIONS.get(code, parts[-1].strip())
                    formatted_messages.append(f"• {message}")

            response_text = (
                f"⚠️ Problemas encontrados na query:\n```\n" +
                "\n".join(formatted_messages) +
                f"\n```\nAqui está uma versão corrigida automaticamente:\n```\n{fixed_query}\n```"
            )

        # Envia a resposta ao Slack na thread
        payload = {
            "channel": channel_id,
            "text": response_text,
            "thread_ts": thread_ts
        }
        requests.post("https://slack.com/api/chat.postMessage", headers=HEADERS, json=payload)

    except Exception as e:
        error_message = f"🚨 Ocorreu um erro ao processar a query: {str(e)}"
        payload = {
            "channel": channel_id,
            "text": error_message,
            "thread_ts": thread_ts
        }
        requests.post("https://slack.com/api/chat.postMessage", headers=HEADERS, json=payload)

@app.route('/slack', methods=['POST'])
def handle_slack_event():
    data = request.form  # Slack envia os dados como 'form-urlencoded'
    query = data.get('text', '').strip()
    response_url = data.get('response_url')  # URL para responder ao Slack
    channel_id = data.get('channel_id')  # ID do canal
    thread_ts = data.get('thread_ts', data.get('ts'))  # Timestamp da thread ou mensagem original

    # Resposta inicial com saudação amigável
    if not query:
        return Response("⚠️ Nenhuma query SQL encontrada! Por favor, envie uma query válida.", status=200)

    # Processa a query em segundo plano
    threading.Thread(target=process_query, args=(query, channel_id, response_url, thread_ts)).start()

    return Response("🔄 Sua query está sendo analisada. Responderemos em instantes na thread.", status=200)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
