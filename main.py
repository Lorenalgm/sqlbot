from flask import Flask, request, jsonify, Response
import subprocess
import threading
import requests
import os

app = Flask(__name__)

# Traduções específicas para mensagens relacionadas a UPDATE no PostgreSQL
TRANSLATIONS = {
    "L016": "Use sempre uma cláusula WHERE ao fazer UPDATE ou DELETE para evitar alterações em massa.",
    "L019": "Faltando um espaço após a vírgula na cláusula SET.",
    "L040": "As colunas na cláusula SET não estão corretamente separadas por vírgulas.",
    "L042": "Faltando uma palavra-chave explícita como WHERE ou RETURNING após o comando UPDATE.",
    "L044": "Evite usar tabelas sem alias em consultas complexas com UPDATE.",
    "L027": "Os operadores na cláusula SET devem ter um espaço antes e depois (e.g., =).",
    "ambiguous.where_clause": "Cláusula WHERE ausente ou ambígua. Certifique-se de filtrar os resultados corretamente ao usar UPDATE.",
    "ambiguous.column_count": "O comando UPDATE parece estar incompleto ou mal definido."
}

def process_query(query, response_url):
    """Processa a query em segundo plano e envia a resposta ao Slack."""
    try:
        # Salva a query em um arquivo temporário
        with open("temp.sql", "w") as f:
            f.write(query)

        # Executa o SQLFluff para validar a query
        result = subprocess.run(
            ["sqlfluff", "lint", "--dialect", "postgres", "temp.sql"],
            capture_output=True,
            text=True
        )

        # Processa a saída do SQLFluff
        lint_output = result.stdout.strip()
        if not lint_output:
            response_text = "✅ Nenhum problema encontrado na query! Tudo certo."
        else:
            # Formata a saída do SQLFluff
            formatted_messages = []
            for line in lint_output.splitlines():
                if "L:" in line and "|" in line:
                    parts = line.split("|")
                    code = parts[-1].strip()
                    message = TRANSLATIONS.get(code, parts[-1].strip())
                    formatted_messages.append(f"• {message}")

            response_text = "⚠️ Problemas encontrados na query:\n```\n" + "\n".join(formatted_messages) + "\n```"

        # Envia a resposta ao Slack
        requests.post(response_url, json={"text": response_text})

    except Exception as e:
        error_message = f"🚨 Ocorreu um erro ao processar a query: {str(e)}"
        requests.post(response_url, json={"text": error_message})

@app.route('/slack', methods=['POST'])
def handle_slack_event():
    data = request.form  # Slack envia os dados como 'form-urlencoded'
    query = data.get('text', '').strip()
    response_url = data.get('response_url')  # URL para responder ao Slack

    # Resposta inicial rápida
    if not query:
        return Response("⚠️ Nenhuma query SQL encontrada! Por favor, envie uma query válida.", status=200)

    # Processa a query em segundo plano
    threading.Thread(target=process_query, args=(query, response_url)).start()

    # Retorna imediatamente ao Slack para evitar timeout
    return Response("🔄 Sua query está sendo analisada. Aguarde...", status=200)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
