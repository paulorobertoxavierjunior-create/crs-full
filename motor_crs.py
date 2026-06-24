import os
import json
import time
from flask import Flask, request, jsonify
from flask_cors import CORS  # Garante que o front consiga conversar sem travar
import google.generativeai as genai
from supabase import create_client, Client

app = Flask(__name__)
CORS(app) # Libera requisições vindas do GitHub Pages e Localhost

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
@app.route("/api/crs/processar", methods=["POST"])
def processar_interacao_crs():
    dados = request.json or {}
    mensagem_usuario = dados.get("mensagem")
    sinais_tempo = dados.get("ritmo", {})
    
    # Captura a API Key externa enviada pelo painel (pode vir no header ou no payload)
    chave_api_externa = request.headers.get("Authorization") or dados.get("api_key_externa")

    if not mensagem_usuario:
        return jsonify({"error": "Mensagem vazia"}), 400

    if not chave_api_externa or len(chave_api_externa.strip()) < 10:
        return jsonify({"error": "API Key do Gemini inválida ou ausente no painel."}), 400

    # 1. Configura o Motor Cognitivo CRS
    analise = MotorCognitivoCRS.calcular_vetor_ritmo(sinais_tempo)
    
    # 2. Conexão Real com o Gemini e Engenharia de Prompt Rítmica
    try:
        # Força o SDK a ignorar rotas beta instáveis do Render e usar a API v1 estável
        os.environ["GOOGLE_API_VERSION"] = "v1"
        genai.configure(api_key=chave_api_externa.replace("Bearer ", "").strip())
        
        prompt_sistema = (
            f"Você é o agente central Elayon CRS integrado ao painel simbiótico. "
            f"Sua cognição foi sintonizada ao ritmo do emissor. "
            f"Diretriz de Cadência Atual: {analise['diretriz']}"
        )
        
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config={"temperature": 0.7},
            system_instruction=prompt_sistema
        )
        
        response = model.generate_content(mensagem_usuario)
        resposta_ia = response.text

    except Exception as gemini_err:
        return jsonify({"error": f"Erro na conexão com o Gemini: {str(gemini_err)}"}), 500

    # 3. Registra os resultados no Supabase para análise gráfica do Criador
    if supabase:
        try:
            supabase.table("crs_consumo_metricas").insert({
                "silencio_pct": sinais_tempo.get("silencio_pct", 0),
                "hesitacao_pct": sinais_tempo.get("hesitacao_pct", 0),
                "tokens_consumidos": len(mensagem_usuario.split()) * 2 
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
