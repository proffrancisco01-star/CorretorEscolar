# ==============================================================
# FICHEIRO: app.py
# DESCRIÇÃO: Corretor Escolar Mobile com emissão de cartões em lote
#            (2 cartões A5 por folha A4) e suporte a câmara.
# LINGUAGEM: Python 3
# ==============================================================

import json
import os
import io
import qrcode
import streamlit as st

# Importações da biblioteca ReportLab para geração do PDF em A4
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader

# Configuração da página Web para visualização móvel
st.set_page_config(
    page_title="Corretor Escolar Mobile",
    page_icon="📱",
    layout="centered"
)

FICHEIRO_ALUNOS = "banco_alunos.json"
FICHEIRO_PROVAS = "banco_provas.json"


def carregar_dados(caminho):
    """Lê dados de um ficheiro JSON local com suporte a UTF-8."""
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


def gerar_qr_code(texto):
    """Cria uma imagem de QR Code na memória a partir de um texto."""
    qr = qrcode.QRCode(version=1, box_size=3, border=1)
    qr.add_data(texto)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer_qr = io.BytesIO()
    img.save(buffer_qr, format="PNG")
    buffer_qr.seek(0)
    return buffer_qr


def desenhar_cartao_a5(p, aluno, prova, y_offset):
    """
    Desenha um único cartão-resposta A5 dentro de uma metade da folha A4.
    y_offset: deslocamento vertical (0 para metade inferior, 421 para metade superior).
    """
    largura = 595.27  # Largura total A4 em pontos
    altura_a5 = 420.94 # Altura de meia folha A4

    # 1. MARCADORES DE CANTO PARA ENQUADRAMENTO DA CÂMARA (Quadrados Pretos)
    p.setFillColor(colors.black)
    p.rect(20, y_offset + altura_a5 - 30, 14, 14, fill=1)                   # Topo Esquerda
    p.rect(largura - 34, y_offset + altura_a5 - 30, 14, 14, fill=1)          # Topo Direita
    p.rect(20, y_offset + 20, 14, 14, fill=1)                               # Base Esquerda
    p.rect(largura - 34, y_offset + 20, 14, 14, fill=1)                     # Base Direita

    # 2. CABEÇALHO DO CARTÃO
    p.setFont("Helvetica-Bold", 11)
    p.drawString(45, y_offset + altura_a5 - 25, "CARTÃO-RESPOSTA - CORRETOR ESCOLAR")
    
    p.setFont("Helvetica", 8)
    p.drawString(45, y_offset + altura_a5 - 40, f"Aluno: {aluno['nome']}")
    p.drawString(45, y_offset + altura_a5 - 52, f"CPF/Matrícula: {aluno['cpf']}  |  Turma: {aluno['turma']}")
    p.drawString(45, y_offset + altura_a5 - 64, f"Avaliação: {prova['nome_prova']}")

    # 3. QR CODE DE IDENTIFICAÇÃO AUTOMÁTICA
    dados_qr = f"{aluno['cpf']}|{prova['nome_prova']}"
    buffer_qr = gerar_qr_code(dados_qr)
    p.drawImage(ImageReader(buffer_qr), largura - 95, y_offset + altura_a5 - 75, width=55, height=55)

    # Linha divisória interna do cabeçalho
    p.setStrokeColor(colors.black)
    p.setLineWidth(0.5)
    p.line(45, y_offset + altura_a5 - 80, largura - 45, y_offset + altura_a5 - 80)

    # 4. GERAÇÃO DAS QUESTÕES E BOLINHAS (Até 30 questões)
    qtd_q = min(int(prova["qtd_questoes"]), 30)
    qtd_alt = int(prova["qtd_alternativas"])
    letras = ["A", "B", "C", "D", "E"][:qtd_alt]

    pos_y_inicial = y_offset + altura_a5 - 100
    espacamento_y = 18
    pos_x_inicial = 55

    p.setFont("Helvetica-Bold", 8)
    questoes_por_coluna = 15

    for i in range(qtd_q):
        coluna = i // questoes_por_coluna
        indice_na_coluna = i % questoes_por_coluna

        x_base = pos_x_inicial + (coluna * 240)
        y_base = pos_y_inicial - (indice_na_coluna * espacamento_y)

        # Número da questão
        p.setFillColor(colors.black)
        p.drawString(x_base, y_base, f"{i+1:02d}.")

        # Bolinhas de resposta
        for j, letra in enumerate(letras):
            x_bolinha = x_base + 25 + (j * 32)
            y_bolinha = y_base + 3

            p.setStrokeColor(colors.black)
            p.setFillColor(colors.white)
            p.circle(x_bolinha, y_bolinha, 6, stroke=1, fill=0)

            p.setFillColor(colors.black)
            p.setFont("Helvetica", 6)
            p.drawCentredString(x_bolinha, y_bolinha - 2, letra)
            p.setFont("Helvetica-Bold", 8)


def gerar_pdf_turma_a4(alunos_turma, prova):
    """
    Gera um único PDF em formato A4 contendo 2 cartões A5 por página
    para toda a turma selecionada.
    """
    buffer_pdf = io.BytesIO()
    p = canvas.Canvas(buffer_pdf, pagesize=A4)
    largura, altura = A4

    for index, aluno in enumerate(alunos_turma):
        posicao_na_pagina = index % 2
        
        if posicao_na_pagina == 0:
            # Cartão na metade superior da folha
            desenhar_cartao_a5(p, aluno, prova, y_offset=altura / 2)
        else:
            # Cartão na metade inferior da folha
            desenhar_cartao_a5(p, aluno, prova, y_offset=0)
            
            # Linha tracejada horizontal de corte no meio da folha
            p.setDash(3, 3)
            p.line(0, altura / 2, largura, altura / 2)
            p.setDash()  # Restaura linha contínua
            p.showPage() # Finaliza a página A4 com os 2 cartões

    # Se a quantidade de alunos for ímpar, encerra a última página
    if len(alunos_turma) % 2 != 0:
        p.setDash(3, 3)
        p.line(0, altura / 2, largura, altura / 2)
        p.setDash()
        p.showPage()

    p.save()
    buffer_pdf.seek(0)
    return buffer_pdf


# ==============================================================
# INTERFACE WEB STREAMLIT
# ==============================================================

st.title("📱 Corretor Escolar Mobile")

aba_alunos, aba_provas, aba_cartoes, aba_corrigir = st.tabs([
    "👨‍🎓 Alunos", 
    "📋 Avaliações", 
    "🖨️ Imprimir Turma (A4)", 
    "📷 Corrigir (Câmara)"
])

# --- ABA 1: ALUNOS ---
with aba_alunos:
    st.header("Cadastro de Alunos")
    with st.form("form_aluno", clear_on_submit=True):
        cpf = st.text_input("CPF / Matrícula:")
        nome = st.text_input("Nome Completo:")
        turma = st.text_input("Turma (ex: 9º Ano A):")
        
        if st.form_submit_button("Cadastrar Aluno"):
            if cpf and nome and turma:
                alunos = carregar_dados(FICHEIRO_ALUNOS)
                alunos.append({"cpf": cpf, "nome": nome, "turma": turma.strip().upper()})
                guardar_dados(FICHEIRO_ALUNOS, alunos)
                st.success(f"Aluno {nome} cadastrado!")
                st.rerun()

    st.subheader("Alunos Cadastrados")
    st.dataframe(carregar_dados(FICHEIRO_ALUNOS), use_container_width=True)

# --- ABA 2: AVALIAÇÕES ---
with aba_provas:
    st.header("Cadastro de Avaliações")
    with st.form("form_prova", clear_on_submit=True):
        nome_prova = st.text_input("Nome da Avaliação:")
        qtd_questoes = st.number_input("Qtd. Questões (Máx: 30):", min_value=1, max_value=30, value=10)
        qtd_alternativas = st.selectbox("Alternativas por Questão:", [4, 5])
        gabarito = st.text_input("Gabarito Oficial (Ex: 1A, 2C, 3D...):")
        
        if st.form_submit_button("Salvar Avaliação"):
            if nome_prova and gabarito:
                provas = carregar_dados(FICHEIRO_PROVAS)
                provas.append({
                    "nome_prova": nome_prova,
                    "qtd_questoes": int(qtd_questoes),
                    "qtd_alternativas": int(qtd_alternativas),
                    "gabarito": gabarito.upper()
                })
                guardar_dados(FICHEIRO_PROVAS, provas)
                st.success("Avaliação salva!")
                st.rerun()

    st.subheader("Avaliações Cadastradas")
    st.dataframe(carregar_dados(FICHEIRO_PROVAS), use_container_width=True)

# --- ABA 3: IMPRESSÃO EM LOTE POR TURMA (A4) ---
with aba_cartoes:
    st.header("🖨️ Emissão de Cartões da Turma em A4")
    st.write("Gera 1 folha A4 para cada 2 alunos, com linha tracejada para corte ao meio.")

    alunos_lista = carregar_dados(FICHEIRO_ALUNOS)
    provas_lista = carregar_dados(FICHEIRO_PROVAS)

    if not alunos_lista or not provas_lista:
        st.info("Cadastre pelo menos um aluno e uma avaliação para gerar os cartões.")
    else:
        # Extrai lista de turmas únicas
        turmas_disponiveis = sorted(list(set(a["turma"] for a in alunos_lista if "turma" in a)))
        
        turma_selecionada = st.selectbox("Selecione a Turma:", turmas_disponiveis)
        
        opcoes_provas = {f"{p['nome_prova']} ({p['qtd_questoes']}Q / {p['qtd_alternativas']}Alt)": p for p in provas_lista}
        prova_selecionada_nome = st.selectbox("Selecione a Avaliação:", list(opcoes_provas.keys()))
        prova_obj = opcoes_provas[prova_selecionada_nome]

        # Filtra alunos da turma
        alunos_da_turma = [a for a in alunos_lista if a.get("turma") == turma_selecionada]
        
        st.write(f"**Total de alunos na turma {turma_selecionada}:** {len(alunos_da_turma)}")

        if st.button("Gerar PDF da Turma Completa (A4)"):
            pdf_bytes = gerar_pdf_turma_a4(alunos_da_turma, prova_obj)
            
            st.success("PDF da turma gerado com sucesso!")
            st.download_button(
                label="📥 Baixar PDF da Turma (Formato A4)",
                data=pdf_bytes,
                file_name=f"Cartoes_Turma_{turma_selecionada}_{prova_obj['nome_prova']}.pdf",
                mime="application/pdf"
            )

# --- ABA 4: CORREÇÃO VIA CÂMARA ---
with aba_corrigir:
    st.header("📷 Leitura e Correção do Gabarito")
    st.write("Enquadre o cartão-resposta A5 focando nos 4 marcadores dos cantos.")
    
    foto_cartao = st.camera_input("Capturar Cartão-Resposta")
    
    if foto_cartao is not None:
        st.image(foto_cartao, caption="Foto capturada", use_column_width=True)
        st.success("Foto recebida com sucesso! Na próxima etapa ativaremos o processamento OpenCV dos 4 cantos.")