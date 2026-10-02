# ==============================================================
# FICHEIRO: app.py
# DESCRIÇÃO: Corretor Escolar Mobile estilo MobiEduca-me com 
#            leitura de QR Code, enquadramento visual de bolinhas,
#            sinal sonoro (bip) e geração de cartões A4.
# LINGUAGEM: Python 3
# ==============================================================

import json
import os
import io
import re
import cv2
import numpy as np
import qrcode
import streamlit as st

# Importações para geração de PDF com ReportLab
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(
    page_title="Corretor Escolar Mobile",
    page_icon="📱",
    layout="centered"
)

# 2. INJEÇÃO DE CSS PARA GARANTIR A CÂMARA EM TAMANHO GRANDE NO TELEMÓVEL
st.markdown("""
    <style>
    /* Força o contentor da câmara a usar 100% da largura */
    [data-testid="stCameraInput"] {
        width: 100% !important;
        max-width: 100% !important;
    }
    
    /* Define altura e proporção adequadas para o vídeo da câmara */
    [data-testid="stCameraInput"] video {
        width: 100% !important;
        min-height: 380px !important;
        height: 60vh !important;
        object-fit: cover !important;
        border-radius: 12px;
        border: 3px solid #007bff;
    }

    /* Otimiza o botão de tirar foto */
    [data-testid="stCameraInput"] button {
        width: 100% !important;
        padding: 14px !important;
        font-size: 18px !important;
        font-weight: bold !important;
    }
    </style>
""", unsafe_allow_html=True)

FICHEIRO_ALUNOS = "banco_alunos.json"
FICHEIRO_PROVAS = "banco_provas.json"

# ==============================================================
# FUNÇÕES DE GESTÃO DE DADOS (JSON)
# ==============================================================

def carregar_dados(caminho):
    """Lê ficheiros JSON locais. Retorna lista vazia se não existir."""
    if not os.path.exists(caminho):
        return []
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def guardar_dados(caminho, dados):
    """Guarda a lista de dados num ficheiro JSON local."""
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)

# ==============================================================
# FUNÇÕES DE IMPRESSÃO (REPORTLAB - CARTÕES A5 EM A4)
# ==============================================================

def gerar_qr_code(texto):
    """Gera uma imagem PNG de QR Code na memória."""
    qr = qrcode.QRCode(version=1, box_size=3, border=1)
    qr.add_data(texto)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer_qr = io.BytesIO()
    img.save(buffer_qr, format="PNG")
    buffer_qr.seek(0)
    return buffer_qr


def desenhar_cartao_a5(p, aluno, prova, y_offset):
    """Desenha um cartão-resposta A5 numa das metades da folha A4."""
    largura = 595.27
    altura_a5 = 420.94

    # Marcadores de Canto Pretos (Quadrados para sincronização visual)
    p.setFillColor(colors.black)
    p.rect(20, y_offset + altura_a5 - 30, 14, 14, fill=1)                   # Topo Esquerda
    p.rect(largura - 34, y_offset + altura_a5 - 30, 14, 14, fill=1)          # Topo Direita
    p.rect(20, y_offset + 20, 14, 14, fill=1)                               # Base Esquerda
    p.rect(largura - 34, y_offset + 20, 14, 14, fill=1)                     # Base Direita

    # Cabeçalho do Cartão
    p.setFont("Helvetica-Bold", 11)
    p.drawString(45, y_offset + altura_a5 - 25, "CARTÃO-RESPOSTA - CORRETOR ESCOLAR")
    
    p.setFont("Helvetica", 8)
    p.drawString(45, y_offset + altura_a5 - 40, f"Aluno: {aluno['nome']}")
    p.drawString(45, y_offset + altura_a5 - 52, f"CPF/Matrícula: {aluno['cpf']}  |  Turma: {aluno['turma']}")
    p.drawString(45, y_offset + altura_a5 - 64, f"Avaliação: {prova['nome_prova']}")

    # Inserção do QR Code
    dados_qr = f"{aluno['cpf']}|{prova['nome_prova']}"
    buffer_qr = gerar_qr_code(dados_qr)
    p.drawImage(ImageReader(buffer_qr), largura - 95, y_offset + altura_a5 - 75, width=55, height=55)

    # Linha Divisória
    p.setStrokeColor(colors.black)
    p.setLineWidth(0.5)
    p.line(45, y_offset + altura_a5 - 80, largura - 45, y_offset + altura_a5 - 80)

    # Geração do Gabarito (Grade de Bolinhas)
    qtd_q = min(int(prova["qtd_questoes"]), 30)
    qtd_alt = int(prova["qtd_alternativas"])
    letras = ["A", "B", "C", "D", "E"][:qtd_alt]

    pos_y_inicial = y_offset + altura_a5 - 100
    espacamento_y = 18
    pos_x_inicial = 55
    questoes_por_coluna = 15

    for i in range(qtd_q):
        coluna = i // questoes_por_coluna
        indice_na_coluna = i % questoes_por_coluna

        x_base = pos_x_inicial + (coluna * 240)
        y_base = pos_y_inicial - (indice_na_coluna * espacamento_y)

        p.setFont("Helvetica-Bold", 8)
        p.setFillColor(colors.black)
        p.drawString(x_base, y_base, f"{i+1:02d}.")

        for j, letra in enumerate(letras):
            x_bolinha = x_base + 25 + (j * 32)
            y_bolinha = y_base + 3

            p.setStrokeColor(colors.black)
            p.setFillColor(colors.white)
            p.circle(x_bolinha, y_bolinha, 6, stroke=1, fill=0)

            p.setFillColor(colors.black)
            p.setFont("Helvetica", 6)
            p.drawCentredString(x_bolinha, y_bolinha - 2, letra)


def gerar_pdf_turma_a4(alunos_turma, prova):
    """Gera o ficheiro PDF final em A4 com 2 cartões por página."""
    buffer_pdf = io.BytesIO()
    p = canvas.Canvas(buffer_pdf, pagesize=A4)
    largura, altura = A4

    for index, aluno in enumerate(alunos_turma):
        posicao = index % 2
        if posicao == 0:
            desenhar_cartao_a5(p, aluno, prova, y_offset=altura / 2)
        else:
            desenhar_cartao_a5(p, aluno, prova, y_offset=0)
            p.setDash(3, 3)
            p.line(0, altura / 2, largura, altura / 2)
            p.setDash()
            p.showPage()

    if len(alunos_turma) % 2 != 0:
        p.setDash(3, 3)
        p.line(0, altura / 2, largura, altura / 2)
        p.setDash()
        p.showPage()

    p.save()
    buffer_pdf.seek(0)
    return buffer_pdf

# ==============================================================
# FUNÇÕES DE PROCESSAMENTO DE IMAGEM E LEITURA (OPENCV)
# ==============================================================

def reproduzir_som_bip():
    """Gera um aviso sonoro (bip) usando HTML/JS no navegador."""
    som_html = """
        <audio autoplay>
            <source src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3" type="audio/mpeg">
        </audio>
    """
    st.components.v1.html(som_html, height=0, width=0)


def processar_imagem_gabarito(bytes_imagem, prova_selecionada):
    """
    Lê a foto capturada, deteta o QR Code, analisa o enquadramento
    e desenha marcações vermelhas/verdes nas bolinhas lidas.
    """
    # Converter bytes da imagem para formato OpenCV (NumPy Array)
    nparr = np.frombuffer(bytes_imagem, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        return None, "Erro ao carregar a imagem.", None

    # 1. Leitura do QR Code via OpenCV
    detector_qr = cv2.QRCodeDetector()
    dados_qr, pontos_qr, _ = detector_qr.detectAndDecode(img)
    
    # Desenhar retângulo verde em volta do QR Code se encontrado
    if pontos_qr is not None and len(pontos_qr) > 0:
        pts = np.int32(pontos_qr).reshape((-1, 1, 2))
        cv2.polylines(img, [pts], True, (0, 255, 0), 3)

    # 2. Converter para escala de cinzentos para análise visual
    cinza = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(cinza, (5, 5), 0)
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # 3. Identificar contornos circulares (bolinhas)
    contornos, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    bolinhas_detetadas = 0
    for c in contornos:
        perimetro = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * perimetro, True)
        area = cv2.contourArea(c)
        
        # Filtrar por área e formato circular
        if 80 < area < 1200 and len(approx) > 5:
            bolinhas_detetadas += 1
            # Desenha um círculo vermelho na ecrã para mostrar o enquadramento
            (x, y), raio = cv2.minEnclosingCircle(c)
            cv2.circle(img, (int(x), int(y)), int(raio), (0, 0, 255), 2)

    # Converter imagem processada de volta para exibição no Streamlit
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    return img_rgb, dados_qr, bolinhas_detetadas

# ==============================================================
# INTERFACE DO UTILIZADOR (STREAMLIT)
# ==============================================================

st.title("📱 Corretor Escolar Mobile")

aba_alunos, aba_provas, aba_cartoes, aba_corrigir = st.tabs([
    "👨‍🎓 Alunos", 
    "📋 Nova Prova / Avaliação", 
    "🖨️ Imprimir Turma (A4)", 
    "📷 Corrigir (Câmara)"
])

# --- ABA 1: CADASTRO DE ALUNOS ---
with aba_alunos:
    st.header("Cadastro de Alunos")
    with st.form("form_aluno", clear_on_submit=True):
        cpf = st.text_input("CPF / Matrícula:")
        nome = st.text_input("Nome Completo:")
        turma = st.text_input("Turma (ex: 9º ANO A):")
        
        if st.form_submit_button("Cadastrar Aluno"):
            if cpf and nome and turma:
                alunos = carregar_dados(FICHEIRO_ALUNOS)
                alunos.append({"cpf": cpf, "nome": nome, "turma": turma.strip().upper()})
                guardar_dados(FICHEIRO_ALUNOS, alunos)
                st.success(f"Aluno {nome} cadastrado com sucesso!")
                st.rerun()

    st.subheader("Alunos Cadastrados")
    st.dataframe(carregar_dados(FICHEIRO_ALUNOS), use_container_width=True)

# --- ABA 2: INSERIR NOVA PROVA / AVALIAÇÃO ---
with aba_provas:
    st.header("📋 Inserir Nova Prova / Avaliação")
    st.write("Preencha os dados abaixo para registar a avaliação e o respetivo gabarito oficial.")
    
    with st.form("form_prova", clear_on_submit=True):
        nome_prova = st.text_input("Nome da Prova / Avaliação (ex: Prova de Matemática Q1):")
        qtd_questoes = st.number_input("Quantidade de Questões (Máx: 30):", min_value=1, max_value=30, value=10)
        qtd_alternativas = st.selectbox("Alternativas por Questão:", [4, 5], index=1)
        gabarito_texto = st.text_input("Gabarito Oficial (ex: 1A, 2C, 3D, 4B...):")
        
        if st.form_submit_button("💾 Salvar Nova Prova"):
            if nome_prova and gabarito_texto:
                provas = carregar_dados(FICHEIRO_PROVAS)
                provas.append({
                    "nome_prova": nome_prova.strip(),
                    "qtd_questoes": int(qtd_questoes),
                    "qtd_alternativas": int(qtd_alternativas),
                    "gabarito": gabarito_texto.upper().strip()
                })
                guardar_dados(FICHEIRO_PROVAS, provas)
                st.success(f"Prova '{nome_prova}' cadastrada com sucesso!")
                st.rerun()
            else:
                st.error("Por favor, preencha o nome da prova e o gabarito oficial.")

    st.subheader("Provas Registadas")
    st.dataframe(carregar_dados(FICHEIRO_PROVAS), use_container_width=True)

# --- ABA 3: IMPRESSÃO EM LOTE (A4) ---
with aba_cartoes:
    st.header("🖨️ Emissão de Cartões da Turma em A4")
    alunos_lista = carregar_dados(FICHEIRO_ALUNOS)
    provas_lista = carregar_dados(FICHEIRO_PROVAS)

    if not alunos_lista or not provas_lista:
        st.info("Cadastre pelo menos um aluno e uma prova para gerar os cartões.")
    else:
        turmas_disponiveis = sorted(list(set(a["turma"] for a in alunos_lista if "turma" in a)))
        turma_selecionada = st.selectbox("Selecione a Turma:", turmas_disponiveis)
        
        opcoes_provas = {f"{p['nome_prova']} ({p['qtd_questoes']}Q / {p['qtd_alternativas']}Alt)": p for p in provas_lista}
        prova_nome_sel = st.selectbox("Selecione a Prova:", list(opcoes_provas.keys()))
        prova_obj = opcoes_provas[prova_nome_sel]

        alunos_da_turma = [a for a in alunos_lista if a.get("turma") == turma_selecionada]

        if st.button("Gerar PDF da Turma Completa (A4)"):
            pdf_bytes = gerar_pdf_turma_a4(alunos_da_turma, prova_obj)
            st.success("PDF gerado com sucesso!")
            st.download_button(
                label="📥 Baixar PDF para Impressão",
                data=pdf_bytes,
                file_name=f"Cartoes_{turma_selecionada}.pdf",
                mime="application/pdf"
            )

# --- ABA 4: CORRIGIR COM CÂMARA (ESTILO MOBIEDUCA-ME) ---
with aba_corrigir:
    st.header("📷 Leitura e Correção Automatizada")
    st.write("Posicione a câmara do telemóvel sobre o cartão-resposta A5 para realizar a leitura.")

    provas_lista = carregar_dados(FICHEIRO_PROVAS)
    
    if not provas_lista:
        st.warning("Cadastre uma prova no separador 'Nova Prova' antes de iniciar as correções.")
    else:
        provas_dict = {p["nome_prova"]: p for p in provas_lista}
        prova_para_corrigir = st.selectbox("Selecione a Prova a Corrigir:", list(provas_dict.keys()))
        
        # Captura de Imagem com a câmara do telemóvel
        foto = st.camera_input("Capturar Cartão-Resposta")

        if foto is not None:
            bytes_foto = foto.getvalue()
            
            # Processa a imagem usando OpenCV
            img_processada, dados_qr, total_bolinhas = processar_imagem_gabarito(
                bytes_foto, 
                provas_dict[prova_para_corrigir]
            )

            # Aciona o bip sonoro ao detetar a leitura
            reproduzir_som_bip()

            # Exibe a imagem processada com as bolinhas enquadradas a vermelho/verde
            st.subheader("🎯 Resultado do Enquadramento")
            st.image(img_processada, caption="Cartão Enquadrado com Marcações de Leitura", use_container_width=True)

            # Apresentação dos resultados
            st.success(f"🔔 Leitura Concluída! ({total_bolinhas} marcadores enquadrados)")
            
            if dados_qr:
                st.info(f"📌 **QR Code Identificado:** {dados_qr}")
            else:
                st.warning("⚠️ QR Code não detetado. Certifique-se de que o canto superior direito do cartão está visível.")