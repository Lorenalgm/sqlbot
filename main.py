from flask import Flask, request, jsonify, Response
import subprocess
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
    "L032": "A ordem das colunas na cláusula SET não segue o padrão definido.",
    "ambiguous.where_clause": "Cláusula WHERE ausente ou ambígua. Certifique-se de filtrar os resultados corretamente ao usar UPDATE.",
    "ambiguous.column_count": "O comando UPDATE parece estar incompleto ou mal definido."
}

@app.route('/slack', methods=['POST'])
def handle_slack_event():
    data = request.form  # Slack envia os dados como 'form-urlencoded'
    query = data.get('text', '').strip()

    # Resposta inicial rápida para evitar timeout
    if not query:
        return Response("⚠️ Nenhuma query SQL encontrada! Por favor, envie uma query válida.", status=200)

    # Salva a query em um arquivo temporário
    with open("temp.sql", "w") as f:
        f.write(query)

    try:
        # Executa o SQLFluff para validar a query
        result = subprocess.run(
            ["sqlfluff", "lint", "--dialect", "postgres", "temp.sql"],
            capture_output=True,
            text=True
        )

        # Processa a saída do SQLFluff
        lint_output = result.stdout.strip()
        if not lint_output:
            return jsonify({"text": "✅ Nenhum problema encontrado na query! Tudo certo."})

        # Formata a saída do SQLFluff
        formatted_messages = []
        for line in lint_output.splitlines():
            if "L:" in line and "|" in line:
                # Extração da mensagem e código
                parts = line.split("|")
                code = parts[-1].strip()
                message = TRANSLATIONS.get(code, parts[-1].strip())
                formatted_messages.append(f"• {message}")

        # Resposta formatada para o Slack
        response_text = "⚠️ Problemas encontrados na query:\n```\n" + "\n".join(formatted_messages) + "\n```"
        return jsonify({"text": response_text})

    except Exception as e:
        # Captura e retorna erros inesperados
        return jsonify({"text": f"🚨 Ocorreu um erro ao processar a query: {str(e)}"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
