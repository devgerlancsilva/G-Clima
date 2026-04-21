import pytest
from g_clima import GClima

def test_traduzir_wmo():
    app = GClima()
    texto, emoji = app.traduzir_wmo(0)
    assert texto == "Céu limpo"
    assert emoji == "☀️"
    
    texto_desc, emoji_desc = app.traduzir_wmo(999)
    assert texto_desc == "Desconhecido"

def test_calcular_estatisticas():
    app = GClima()
    dados_mock = {
        "temps": [20, 30, 25],
        "umidade": [50, 60],
        "chuva": [0, 0],
        "codigos": [0, 0, 1]
    }
    stats = app.calcular_estatisticas(dados_mock)
    
    assert stats["temps"]["min"] == 20
    assert stats["temps"]["max"] == 30
    assert stats["temps"]["media"] == 25.0
    assert stats["condicao"][0] == "Céu limpo"

def test_buscar_coordenadas_invalidas():
    app = GClima()
    # Cidade inexistente para forçar erro/vazio
    lat, lon = app.buscar_coordenadas("CidadeQueNaoExiste123456")
    assert lat is None
    assert lon is None
