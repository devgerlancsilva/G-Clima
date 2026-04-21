"""
g-clima — Gerador de Relatório do Clima
Busca dados de temperatura de uma cidade e salva um gráfico em PNG.
Utiliza a API gratuita Open-Meteo (sem precisar de chave de API).
"""

import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
import os
import sys

# Garante que a saída do terminal suporte caracteres Unicode (importante no Windows)
if sys.stdout.encoding != 'utf-8':
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except Exception:
        pass

# ── Dependências opcionais ────────────────────────────────────────────────────
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    MATPLOTLIB_OK = True
except ImportError:
    MATPLOTLIB_OK = False

# ── Configuração de cidades populares (lat, lon) ──────────────────────────────
CIDADES = {
    "São Paulo":      (-23.5505, -46.6333),
    "Rio de Janeiro": (-22.9068, -43.1729),
    "Brasília":       (-15.7801, -47.9292),
    "Salvador":       (-12.9714, -38.5014),
    "Fortaleza":      (-3.7172,  -38.5433),
    "Arapiraca":      (-9.7528,  -36.6614),
    "Recife":         (-8.0476,  -34.8770),
    "Manaus":         (-3.1190,  -60.0217),
    "Curitiba":       (-25.4284, -49.2733),
    "Porto Alegre":   (-30.0346, -51.2177),
}

# ── Mapeamento de códigos WMO (Clima) ─────────────────────────────────────────
WMO_CODES = {
    0:  ("Céu limpo", "☀️"),
    1:  ("Principalmente limpo", "🌤️"),
    2:  ("Parcialmente nublado", "⛅"),
    3:  ("Nublado", "☁️"),
    45: ("Nevoeiro", "🌫️"),
    48: ("Nevoeiro com geada", "🌫️"),
    51: ("Drizzle leve", "🌧️"),
    53: ("Drizzle moderado", "🌧️"),
    55: ("Drizzle denso", "🌧️"),
    61: ("Chuva leve", "🌦️"),
    63: ("Chuva moderada", "🌧️"),
    65: ("Chuva forte", "🌧️"),
    71: ("Neve leve", "❄️"),
    73: ("Neve moderada", "❄️"),
    75: ("Neve forte", "❄️"),
    80: ("Pancadas de chuva leves", "🌦️"),
    81: ("Pancadas de chuva moderadas", "🌧️"),
    82: ("Pancadas de chuva violentas", "⛈️"),
    95: ("Trovoada", "⚡"),
}

def traduzir_wmo(code: int):
    return WMO_CODES.get(code, ("Desconhecido", "❓"))

# ── Funções auxiliares ────────────────────────────────────────────────────────

def buscar_coordenadas(cidade: str):
    """Busca lat/lon de qualquer cidade via Geocoding API."""
    url = (
        "https://geocoding-api.open-meteo.com/v1/search?"
        + urllib.parse.urlencode({"name": cidade, "count": 1, "language": "pt"})
    )
    with urllib.request.urlopen(url, timeout=10) as r:
        dados = json.loads(r.read())
    resultados = dados.get("results", [])
    if not resultados:
        return None, None
    return resultados[0]["latitude"], resultados[0]["longitude"]


def buscar_clima(lat: float, lon: float, dias_passados: int = 7, dias_previsao: int = 0):
    """Busca dados climáticos (histórico e/ou previsão)."""
    params = {
        "latitude":            lat,
        "longitude":           lon,
        "hourly":              "temperature_2m,relative_humidity_2m,precipitation,weather_code",
        "timezone":            "America/Sao_Paulo",
    }

    if dias_passados > 0:
        data_fim   = datetime.now().strftime("%Y-%m-%d")
        data_inicio = (datetime.now() - timedelta(days=dias_passados)).strftime("%Y-%m-%d")
        params["start_date"] = data_inicio
        params["end_date"] = data_fim
    
    if dias_previsao > 0:
        params["forecast_days"] = dias_previsao

    url = f"https://api.open-meteo.com/v1/forecast?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.loads(r.read())


def processar_dados(dados: dict):
    """Retorna dicionário com listas de dados processados."""
    h = dados["hourly"]
    datas = [datetime.fromisoformat(t) for t in h["time"]]
    return {
        "datas": datas,
        "temps": h["temperature_2m"],
        "umidade": h.get("relative_humidity_2m"),
        "chuva": h.get("precipitation"),
        "codigos": h.get("weather_code"),
    }


def calcular_estatisticas(dados_proc: dict):
    """Calcula estatísticas para as métricas disponíveis."""
    res = {}
    for chave in ["temps", "umidade", "chuva"]:
        lista = [v for v in dados_proc.get(chave, []) if v is not None]
        if not lista:
            continue
        res[chave] = {
            "min":   round(min(lista), 1),
            "max":   round(max(lista), 1),
            "media": round(sum(lista) / len(lista), 1),
        }
    
    # Condição predominante
    if dados_proc.get("codigos"):
        from collections import Counter
        codes = [c for c in dados_proc["codigos"] if c is not None]
        if codes:
            mais_comum = Counter(codes).most_common(1)[0][0]
            res["condicao"] = traduzir_wmo(mais_comum)
            
    return res


def salvar_grafico(dados_proc, cidade: str, stats: dict, arquivo: str, comparacao=None):
    """Gera e salva o gráfico. Suporta métricas múltiplas ou comparação."""
    if not MATPLOTLIB_OK:
        print("\n⚠  Matplotlib não encontrado. O gráfico PNG não será gerado.")
        return False

    fig, ax1 = plt.subplots(figsize=(12, 6))
    datas = dados_proc["datas"]
    
    if comparacao:
        # Modo Comparação (Apenas Temperatura)
        ax1.plot(datas, dados_proc["temps"], label=cidade, color="#2196F3", linewidth=2)
        ax1.plot(datas, comparacao["dados"]["temps"], label=comparacao["nome"], color="#F44336", linewidth=2)
        ax1.set_ylabel("Temperatura (°C)")
        ax1.set_title(f"Comparação de Temperatura: {cidade} vs {comparacao['nome']}", fontweight="bold")
    else:
        # Modo Normal (Temp + Umidade)
        ax1.plot(datas, dados_proc["temps"], color="#2196F3", linewidth=2, label="Temp (°C)")
        ax1.fill_between(datas, dados_proc["temps"], min(dados_proc["temps"]), alpha=0.1, color="#2196F3")
        ax1.set_ylabel("Temperatura (°C)", color="#1976D2")
        ax1.tick_params(axis='y', labelcolor="#1976D2")

        if dados_proc.get("umidade"):
            ax2 = ax1.twinx()
            ax2.plot(datas, dados_proc["umidade"], color="#4CAF50", linewidth=1, alpha=0.6, label="Umidade (%)")
            ax2.set_ylabel("Umidade (%)", color="#388E3C")
            ax2.tick_params(axis='y', labelcolor="#388E3C")
            ax2.set_ylim(0, 105)

        cond, emoji = stats.get("condicao", ("Desconhecido", ""))
        ax1.set_title(f"Clima em {cidade} — {cond} {emoji}", fontsize=15, fontweight="bold", pad=15)

    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m\n%Hh"))
    ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax1.grid(True, alpha=0.2)
    ax1.legend(loc="upper left")
    
    plt.tight_layout()
    plt.savefig(arquivo, dpi=150)
    plt.close()
    return True


def salvar_pdf(cidade: str, stats: dict, arq_png: str, arq_pdf: str):
    """Gera um relatório PDF elegante com o gráfico e estatísticas."""
    try:
        from fpdf import FPDF
    except ImportError:
        print("⚠  fpdf2 não instalado. Pulando PDF.")
        return False

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", "B", 20)
    
    # Título
    pdf.cell(0, 15, f"Relatório Climático: {cidade}", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(5)
    
    # Estatísticas
    pdf.set_font("helvetica", "B", 14)
    pdf.cell(0, 10, "Resumo do Período:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 12)
    
    cond, emoji = stats.get("condicao", ("Desconhecido", ""))
    pdf.cell(0, 8, f"- Condição Predominante: {cond}", new_x="LMARGIN", new_y="NEXT")
    
    if "temps" in stats:
        s = stats["temps"]
        pdf.cell(0, 8, f"- Temperatura: Min {s['min']}C | Max {s['max']}C | Média {s['media']}C", new_x="LMARGIN", new_y="NEXT")
    
    if "umidade" in stats:
        s = stats["umidade"]
        pdf.cell(0, 8, f"- Umidade Média: {s['media']}%", new_x="LMARGIN", new_y="NEXT")
        
    if "chuva" in stats:
        s = stats["chuva"]
        pdf.cell(0, 8, f"- Precipitação Total: {round(sum([v for v in s.values() if isinstance(v, (int, float))]), 1)}mm (Aprox)", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(10)
    
    # Imagem do gráfico
    if os.path.exists(arq_png):
        pdf.image(arq_png, x=10, w=190)
    
    pdf.set_y(-30)
    pdf.set_font("helvetica", "I", 8)
    pdf.cell(0, 10, f"Gerado por g-clima em {datetime.now().strftime('%d/%m/%Y %H:%M')}", align="C")
    
    pdf.output(arq_pdf)
    return True


def salvar_json(dados_proc, cidade: str, stats: dict, arquivo: str):
    """Salva todos os dados processados em JSON."""
    payload = {
        "cidade":      cidade,
        "gerado_em":   datetime.now().isoformat(),
        "estatisticas": stats,
        "dados_horarios": [
            {
                "hora": d.isoformat(),
                "temp": t,
                "umidade": u,
                "chuva": c,
                "wmo": w
            }
            for d, t, u, c, w in zip(
                dados_proc["datas"], 
                dados_proc["temps"], 
                dados_proc["umidade"], 
                dados_proc["chuva"], 
                dados_proc["codigos"]
            )
        ],
    }
    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


# ── Interface principal ───────────────────────────────────────────────────────

def escolher_cidade():
    print("\n📍 Cidades disponíveis:")
    nomes = list(CIDADES.keys())
    for i, nome in enumerate(nomes, 1):
        print(f"  {i:2}. {nome}")
    print("   0. Digitar outra cidade")

    while True:
        entrada = input("\nEscolha o número (ou 0 para digitar): ").strip()
        if not entrada.isdigit():
            print("   Digite apenas o número.")
            continue
        num = int(entrada)
        if num == 0:
            cidade = input("   Nome da cidade: ").strip()
            lat, lon = buscar_coordenadas(cidade)
            if lat is None:
                print("   ❌ Cidade não encontrada. Tente novamente.")
                continue
            return cidade, lat, lon
        if 1 <= num <= len(nomes):
            nome = nomes[num - 1]
            return nome, *CIDADES[nome]
        print(f"   Digite um número entre 0 e {len(nomes)}.")


def main():
    print("=" * 50)
    print("   🌤  g-clima v2.0 — Relatório Completo")
    print("=" * 50)

    print("\nO que deseja fazer?")
    print("  1. Relatório Histórico (Últimos dias)")
    print("  2. Previsão do Tempo (Próximos dias)")
    print("  3. Comparar duas cidades (Temperatura)")
    
    modo = input("\nEscolha uma opção (1-3, padrão 1): ").strip() or "1"

    if modo == "3":
        print("\n--- Cidade 1 ---")
        c1_nome, c1_lat, c1_lon = escolher_cidade()
        print("\n--- Cidade 2 ---")
        c2_nome, c2_lat, c2_lon = escolher_cidade()
        
        dias = int(input("\nQuantos dias de histórico para comparar? (1-14, padrão 7): ") or 7)
        
        print(f"\n⏳ Comparando {c1_nome} e {c2_nome}…")
        d1 = processar_dados(buscar_clima(c1_lat, c1_lon, dias_passados=dias))
        d2 = processar_dados(buscar_clima(c2_lat, c2_lon, dias_passados=dias))
        
        nome_base = f"comparacao_{c1_nome}_{c2_nome}".lower().replace(" ", "_")
        arq_png = f"{nome_base}.png"
        
        salvar_grafico(d1, c1_nome, {}, arq_png, comparacao={"nome": c2_nome, "dados": d2})
        print(f"\n✅ Gráfico de comparação salvo em: {arq_png}")
        return

    # Modos 1 e 2
    cidade, lat, lon = escolher_cidade()
    
    if modo == "2":
        dias = int(input("\nQuantos dias de previsão? (1-16, padrão 7): ") or 7)
        print(f"\n⏳ Buscando previsão para {cidade}…")
        dados_raw = buscar_clima(lat, lon, dias_passados=0, dias_previsao=dias)
    else:
        dias = int(input("\nQuantos dias de histórico? (1-14, padrão 7): ") or 7)
        print(f"\n⏳ Buscando histórico para {cidade}…")
        dados_raw = buscar_clima(lat, lon, dias_passados=dias)

    dados_proc = processar_dados(dados_raw)
    stats = calcular_estatisticas(dados_proc)

    # Resumo no terminal
    cond, emoji = stats.get("condicao", ("-", ""))
    print(f"\n📊 Resumo para {cidade}: {cond} {emoji}")
    if "temps" in stats:
        t = stats["temps"]
        print(f"   🌡  Temp: {t['min']}°C a {t['max']}°C (Média: {t['media']}°C)")
    if "umidade" in stats:
        print(f"   💧 Umidade Média: {stats['umidade']['media']}%")

    # Arquivos
    sufixo = "previsao" if modo == "2" else "historico"
    nome_base = f"{cidade.lower().replace(' ', '_')}_{sufixo}"
    arq_png = f"clima_{nome_base}.png"
    arq_json = f"clima_{nome_base}.json"
    arq_pdf = f"clima_{nome_base}.pdf"

    # Salva tudo
    sucesso_grafico = salvar_grafico(dados_proc, cidade, stats, arq_png)
    salvar_json(dados_proc, cidade, stats, arq_json)
    sucesso_pdf = salvar_pdf(cidade, stats, arq_png, arq_pdf)

    if sucesso_grafico:
        print(f"\n✅ Gráfico: {arq_png}")
    
    print(f"✅ JSON:    {arq_json}")
    
    if sucesso_pdf:
        print(f"✅ PDF:     {arq_pdf}")

    # Abre os arquivos automaticamente no Windows se solicitado
    if sucesso_pdf or sucesso_grafico:
        abrir = input("\nVisualizar arquivos agora? (S/N, padrão S): ").strip().lower() or "s"
        if abrir == "s":
            try:
                if sucesso_pdf: os.startfile(arq_pdf)
                elif sucesso_grafico: os.startfile(arq_png)
                print("   📂 Abrindo arquivos...")
            except Exception:
                print("   ⚠  Não foi possível abrir os arquivos automaticamente.")

    print("\n🎉 Operação concluída com sucesso!")


if __name__ == "__main__":
    main()
