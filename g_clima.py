"""
g-clima — Gerador de Relatório do Clima
Busca dados de temperatura de uma cidade e salva um gráfico em PNG e relatório PDF.
Utiliza a API gratuita Open-Meteo.
"""

import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
import os
import sys
from typing import Dict, List, Optional, Tuple, Any

# Garante que a saída do terminal suporte caracteres Unicode
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

try:
    from fpdf import FPDF
    FPDF_OK = True
except ImportError:
    FPDF_OK = False

class GClima:
    """Classe principal para gerenciamento de dados climáticos."""

    CIDADES_PADRAO: Dict[str, Tuple[float, float]] = {
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

    WMO_CODES: Dict[int, Tuple[str, str]] = {
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

    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def traduzir_wmo(self, code: int) -> Tuple[str, str]:
        """Traduz o código WMO para texto e emoji."""
        return self.WMO_CODES.get(code, ("Desconhecido", "❓"))

    def buscar_coordenadas(self, cidade: str) -> Tuple[Optional[float], Optional[float]]:
        """Busca latitude e longitude de uma cidade."""
        url = (
            "https://geocoding-api.open-meteo.com/v1/search?"
            + urllib.parse.urlencode({"name": cidade, "count": 1, "language": "pt"})
        )
        try:
            with urllib.request.urlopen(url, timeout=self.timeout) as r:
                dados = json.loads(r.read())
            resultados = dados.get("results", [])
            if not resultados:
                return None, None
            return resultados[0]["latitude"], resultados[0]["longitude"]
        except Exception:
            return None, None

    def buscar_dados_climaticos(self, lat: float, lon: float, 
                               dias_passados: int = 7, 
                               dias_previsao: int = 0) -> Dict[str, Any]:
        """Busca dados da API Open-Meteo."""
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
        with urllib.request.urlopen(url, timeout=self.timeout) as r:
            return json.loads(r.read())

    def processar_dados(self, dados: Dict[str, Any]) -> Dict[str, List[Any]]:
        """Processa a resposta bruta da API."""
        h = dados["hourly"]
        return {
            "datas":   [datetime.fromisoformat(t) for t in h["time"]],
            "temps":   h["temperature_2m"],
            "umidade": h.get("relative_humidity_2m", []),
            "chuva":   h.get("precipitation", []),
            "codigos": h.get("weather_code", []),
        }

    def calcular_estatisticas(self, dados_proc: Dict[str, List[Any]]) -> Dict[str, Any]:
        """Gera estatísticas básicas dos dados processados."""
        res = {}
        for chave in ["temps", "umidade", "chuva"]:
            lista = [v for v in dados_proc.get(chave, []) if v is not None]
            if not lista: continue
            res[chave] = {
                "min":   round(min(lista), 1),
                "max":   round(max(lista), 1),
                "media": round(sum(lista) / len(lista), 1),
            }
        
        if dados_proc.get("codigos"):
            from collections import Counter
            codes = [c for c in dados_proc["codigos"] if c is not None]
            if codes:
                mais_comum = Counter(codes).most_common(1)[0][0]
                res["condicao"] = self.traduzir_wmo(mais_comum)
        return res

    def salvar_grafico(self, dados_proc: Dict[str, List[Any]], cidade: str, 
                        stats: Dict[str, Any], arquivo: str, 
                        comparacao: Optional[Dict[str, Any]] = None) -> bool:
        """Gera o gráfico usando Matplotlib."""
        if not MATPLOTLIB_OK:
            print("\n⚠ Matplotlib não instalado. Pulando gráfico.")
            return False

        fig, ax1 = plt.subplots(figsize=(12, 6))
        datas = dados_proc["datas"]
        
        if comparacao:
            ax1.plot(datas, dados_proc["temps"], label=cidade, color="#2196F3", linewidth=2)
            ax1.plot(datas, comparacao["dados"]["temps"], label=comparacao["nome"], color="#F44336", linewidth=2)
            ax1.set_ylabel("Temperatura (°C)")
            ax1.set_title(f"Comparação: {cidade} vs {comparacao['nome']}", fontweight="bold")
        else:
            ax1.plot(datas, dados_proc["temps"], color="#2196F3", linewidth=2, label="Temp (°C)")
            ax1.fill_between(datas, dados_proc["temps"], min(dados_proc["temps"]), alpha=0.1, color="#2196F3")
            ax1.set_ylabel("Temperatura (°C)", color="#1976D2")
            
            if dados_proc.get("umidade"):
                ax2 = ax1.twinx()
                ax2.plot(datas, dados_proc["umidade"], color="#4CAF50", linewidth=1, alpha=0.4, label="Umidade (%)")
                ax2.set_ylabel("Umidade (%)", color="#388E3C")
                ax2.set_ylim(0, 105)

            cond, emoji = stats.get("condicao", ("Desconhecido", ""))
            ax1.set_title(f"Clima em {cidade} — {cond} {emoji}", fontsize=14, fontweight="bold")

        ax1.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m\n%Hh"))
        ax1.grid(True, alpha=0.2)
        ax1.legend(loc="upper left")
        
        plt.tight_layout()
        plt.savefig(arquivo, dpi=150)
        plt.close()
        return True

    def salvar_pdf(self, cidade: str, stats: Dict[str, Any], 
                   arq_png: str, arq_pdf: str) -> bool:
        """Gera o relatório PDF."""
        if not FPDF_OK:
            print("⚠ fpdf2 não instalado. Pulando PDF.")
            return False

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("helvetica", "B", 20)
        pdf.cell(0, 15, f"Relatório Climático: {cidade}", new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.ln(5)
        
        pdf.set_font("helvetica", "B", 14)
        pdf.cell(0, 10, "Resumo do Período:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("helvetica", "", 12)
        
        cond, emoji = stats.get("condicao", ("-", ""))
        pdf.cell(0, 8, f"- Condição: {cond} {emoji}", new_x="LMARGIN", new_y="NEXT")
        
        for k, v in stats.items():
            if k in ["temps", "umidade"]:
                pdf.cell(0, 8, f"- {k.capitalize()}: Min {v['min']} | Max {v['max']} | Média {v['media']}", new_x="LMARGIN", new_y="NEXT")

        pdf.ln(10)
        if os.path.exists(arq_png):
            pdf.image(arq_png, x=10, w=190)
        
        pdf.output(arq_pdf)
        return True

def main():
    app = GClima()
    print("=" * 50)
    print("   🌤  g-clima v2.1 — Extraordinary Edition")
    print("=" * 50)

    print("\nO que deseja fazer?")
    print("  1. Relatório Histórico")
    print("  2. Previsão do Tempo")
    print("  3. Comparação entre Cidades")
    
    modo = input("\nOpção (1-3, padrão 1): ").strip() or "1"

    if modo == "3":
        print("\n--- Cidade 1 ---")
        c1_nome, c1_lat, c1_lon = escolher_cidade(app)
        print("\n--- Cidade 2 ---")
        c2_nome, c2_lat, c2_lon = escolher_cidade(app)
        dias = int(input("\nDias (1-14, padrão 7): ") or 7)
        
        d1 = app.processar_dados(app.buscar_dados_climaticos(c1_lat, c1_lon, dias))
        d2 = app.processar_dados(app.buscar_dados_climaticos(c2_lat, c2_lon, dias))
        
        arq = f"comparacao_{c1_nome}_{c2_nome}".lower().replace(" ", "_") + ".png"
        app.salvar_grafico(d1, c1_nome, {}, arq, comparacao={"nome": c2_nome, "dados": d2})
        print(f"✅ Salvo em: {arq}")
        os.startfile(arq) if sys.platform == 'win32' else None
        return

    cidade, lat, lon = escolher_cidade(app)
    dias = int(input("\nQuantos dias? (padrão 7): ") or 7)
    
    if modo == "2":
        raw = app.buscar_dados_climaticos(lat, lon, dias_passados=0, dias_previsao=dias)
    else:
        raw = app.buscar_dados_climaticos(lat, lon, dias_passados=dias)

    proc = app.processar_dados(raw)
    stats = app.calcular_estatisticas(proc)

    nome_base = f"{cidade.lower().replace(' ', '_')}"
    png, pdf = f"clima_{nome_base}.png", f"clima_{nome_base}.pdf"

    if app.salvar_grafico(proc, cidade, stats, png): print(f"✅ Gráfico: {png}")
    if app.salvar_pdf(cidade, stats, png, pdf): print(f"✅ PDF: {pdf}")
    
    if sys.platform == 'win32' and (input("\nAbrir arquivos? (S/N): ").lower() == 's'):
        os.startfile(pdf if os.path.exists(pdf) else png)

def escolher_cidade(app: GClima):
    nomes = list(app.CIDADES_PADRAO.keys())
    for i, n in enumerate(nomes, 1): print(f"  {i:2}. {n}")
    print("   0. Outra cidade")

    while True:
        num = input("\nEscolha: ").strip() or "0"
        if num == "0":
            c = input("Nome: ").strip()
            la, lo = app.buscar_coordenadas(c)
            if la: return c, la, lo
            print("❌ Não encontrado.")
        elif num.isdigit() and 1 <= int(num) <= len(nomes):
            n = nomes[int(num)-1]
            return n, *app.CIDADES_PADRAO[n]

if __name__ == "__main__":
    main()
