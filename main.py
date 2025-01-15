from flask import Flask, request, jsonify
import subprocess
import os

app = Flask(__name__)

# Traduções para mensagens de erro do SQLFluff
TRANSLATIONS = {
    "L003": "Evite usar 'SELECT *'. Especifique as colunas que deseja buscar.",
    "L009": "As palavras-chave devem estar em letras maiúsculas.",
    "L010": "Os nomes das tabelas devem estar em minúsculas, conforme o padrão.",
    "L011": "Evite usar aspas duplas para nomes de tabelas ou colunas. Use aspas simples ou sem aspas.",
    "L012": "Os nomes das colunas devem estar em minúsculas.",
    "L014": "Faltando uma vírgula no final desta linha.",
    "L016": "Use sempre uma cláusula WHERE ao fazer UPDATE ou DELETE para evitar alterações em massa.",
    "L019": "Faltando um espaço após a vírgula.",
    "L022": "Faltando a palavra-chave DISTINCT para evitar duplicatas, se necessário.",
    "L023": "Coloque cada cláusula em uma nova linha para melhorar a legibilidade.",
    "L025": "As colunas na cláusula SELECT não estão alinhadas corretamente.",
    "L026": "Evite usar literais numéricos no SQL. Use variáveis ou parâmetros.",
    "L027": "Os operadores devem ter um espaço antes e depois.",
    "L028": "Evite usar o tipo de dado TEXT. Prefira VARCHAR com limite definido.",
    "L029": "Evite duplicação de alias nas colunas selecionadas.",
    "L031": "Certifique-se de que os índices sejam usados corretamente nesta consulta.",
    "L032": "A ordem das colunas não corresponde ao padrão definido na organização.",
    "L034": "Evite usar a função 'COUNT(*)'. Prefira contar uma coluna específica.",
    "L036": "Prefira nomes mais descritivos para as tabelas e colunas.",
    "L040": "As colunas não estão corretamente separadas por vírgulas.",
    "L042": "Faltando uma palavra-chave de junção explícita (JOIN, LEFT JOIN, etc.).",
    "L044": "Evite usar tabelas sem alias para melhorar a legibilidade.",
    "L045": "Prefira funções SQL específicas ao invés de funções genéricas ou personalizadas.",
    "ambiguous.column_count": "A consulta produz um número desconhecido de colunas no resultado. Certifique-se de que todas as colunas estão definidas explicitamente.",
    "ambiguous.join_condition": "Condição de junção ambígua. Verifique se todas as junções estão bem definidas.",
    "ambiguous.where_clause": "Cláusula WHERE ambígua ou ausente. Certifique-se de filtrar os resultados adequadamente."
}

@app.route('/slack', methods=['POST'])
def handle_slack_event():
    data = request.json

    # Extrai a query enviada pelo Slack
    query = data.get('text', '').strip()
    if not query:
        return jsonify({"text": "⚠️ Nenhuma query SQL encontrada! Por favor, envie uma query válida."})

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

    # Retorno para o Slack
    if formatted_messages:
        response_text = "⚠️ Problemas encontrados na query:\n```\n" + "\n".join(formatted_messages) + "\n```"
    else:
        response_text = "✅ Nenhum problema encontrado na query! Tudo certo."

    return jsonify({"text": response_text})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
