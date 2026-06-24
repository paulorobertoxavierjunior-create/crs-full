import os
import json
import time
from flask import Flask, request, jsonify
from supabase import create_client, Client

app = Flask(__name__)

# Conexão Real com a Infraestrutura (Variáveis de Ambiente do Render)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY") # service_role
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL else None

class MotorCognitivoCRS:
    @staticmethod
    def calcular_vetor_ritmo(dados_temporais):
        """
        Lê as métricas de tempo brutas enviadas pelo repositório 'presenca'
        e configura o comportamento da IA.
        """
        silencio = int(dados_temporais.get("silencio_pct", 0))
        hesitacao = int(dados_temporais.get("hesitacao_pct", 0))
        eventos = int(dados_temporais.get("eventos", 0))
        
        # Lógica de Adaptação de Prompt baseada no Tempo Humano
        if silencio > 50 or hesitacao > 40:
            carga_cognitiva = "ALTA"
            diretriz_ia = (
                "O usuário está demonstrando alta hesitação ou pausas longas para formular a ideia. "
                "Responda de forma extremamente paciente, didática, estruturada e acolhedora. "
                "Reduza jargões complexos e guie o raciocínio passo a passo."
            )
        elif eventos > 100 and silencio < 15:
            carga_cognitiva = "ACELERADA"
            diretriz_ia = (
                "O usuário está digitando de forma extremamente rápida, fluida e segura. "
                "Seja direto, preciso, dinâmico e vá direto ao ponto técnico. Evite introduções longas."
            )
        else:
            carga_cognitiva = "ESTÁVEL"
            diretriz_ia = "Mantenha uma resposta equilibrada, profissional e natural."
            
        return {
            "carga": carga_cognitiva,
            "diretriz": diretriz_ia,
            "score_estabilidade": max(0, 100 - (silencio + hesitacao))
        }

# ROTA CENTRAL: Recebe do index do 'presenca' e devolve a resposta inteligente
@app.route("/api/crs/processar", method=["POST"])
def processar_interacao_crs():
    dados = request.json
    mensagem_usuario = dados.get("mensagem")
    sinais_tempo = dados.get("ritmo", {})
    chave_api_externa = request.headers.get("Authorization") # CRS_LIVE_...

    if not mensagem_usuario:
        return jsonify({"error": "Mensagem vazia"}), 400

    # 1. Validação da Chave e Desconto de Tokens no Supabase
    # (Opcional neste estágio de teste, mas estruturado no banco)
    
    # 2. Executa a leitura e configuração rítmica através do Motor
    analise = MotorCognitivoCRS.calcular_vetor_ritmo(sinais_tempo)
    
    # 3. Engenharia de Prompt Dinâmica (Injetando a diretriz temporal na IA)
    system_prompt = f"Você é uma inteligência sensível ao ritmo cognitivo humano. Diretriz de Cadência Atual: {analise['diretriz']}"
    
    # [Aqui entra a chamada real para o provedor injetado no admin (Gemini/OpenAI)]
    # Exemplo conceitual de retorno processado pelo Render:
    resposta_ia = f"[Modo Sensível: Carga {analise['carga']}] Entendi seu comando. Processando com base na sua cadência temporal..."

    # 4. Registra os resultados no Supabase para análise gráfica do Criador
    if supabase:
        try:
            supabase.table("crs_consumo_metricas").insert({
                "silencio_pct": sinais_tempo.get("silencio_pct", 0),
                "hesitacao_pct": sinais_tempo.get("hesitacao_pct", 0),
                "tokens_consumidos": len(mensagem_usuario.split()) * 2 # Estimativa simples
            }).execute()
        except Exception as e:
            print(f"Erro ao salvar métricas no banco: {e}")

    return jsonify({
        "resposta": resposta_ia,
        "analise_ritmo": {
            "carga": analise["carga"],
            "estabilidade": analise["score_estabilidade"]
        }
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
