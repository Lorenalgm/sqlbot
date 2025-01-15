from flask import Flask, request, jsonify
import subprocess
import os

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")

app = Flask(__name__)


@app.route('/slack', methods=['POST'])
def handle_slack_event():
    data = request.json

    # Extrai a query enviada pelo Slack
    query = data.get('text', '').strip()
    if not query:
        return jsonify({"text": "Nenhuma query SQL encontrada!"})

    # Salva a query em um arquivo temporário
    with open("temp.sql", "w") as f:
        f.write(query)

    # Executa o SQLFluff para validar a query
    result = subprocess.run(["sqlfluff", "lint", "temp.sql"],
                            capture_output=True,
                            text=True)

    # Formata a resposta
    lint_output = result.stdout.strip()
    if not lint_output:
        return jsonify({"text": "Nenhum problema encontrado na query!"})

    return jsonify({"text": f"Resultados do Lint:\n```\n{lint_output}\n```"})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
