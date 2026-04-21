# 🌤 g-clima

![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)
![Build Status](https://github.com/devgerlancsilva/G-Clima/actions/workflows/python-app.yml/badge.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Pair Extraordinary](https://img.shields.io/badge/Pair-Extraordinary-gold.svg)

Aplicativo profissional em Python para análise climática avançada — **sem precisar de chave de API**.

---

## ✨ Funcionalidades...

- 🔍 **Busca Avançada**: Temperatura, umidade e precipitação.
- 🔮 **Previsão**: Veja o clima para os próximos 7–16 dias.
- 📊 **Comparação**: Compare o clima entre duas cidades em um único gráfico.
- 📄 **Relatório PDF**: Gera um PDF profissional com gráficos e estatísticas.
- 💾 **Exportação JSON**: Dados brutos completos para desenvolvedores.
- 🧪 **Testes Automatizados**: Suite de testes com `pytest`.
- 🚀 **CI/CD**: Integração contínua com GitHub Actions.

---

## 📦 Instalação

### 1. Clone o repositório
```bash
git clone https://github.com/seu-usuario/g-clima.git
cd g-clima
```

### 2. Instale as dependências
```bash
pip install -r requirements.txt
```

> O script utiliza `matplotlib` para os gráficos e `fpdf2` para a geração dos relatórios PDF.

---

## ▶️ Como usar

```bash
python g_clima.py
```

O programa irá:
1. Mostrar uma lista de cidades populares para escolher
2. Permitir digitar qualquer outra cidade
3. Perguntar quantos dias de histórico você quer (1–14)
4. Buscar os dados e salvar o gráfico + JSON

---

## 📁 Arquivos gerados

| Arquivo | Descrição |
|---|---|
| `clima_sao_paulo.png` | Gráfico de temperatura |
| `clima_sao_paulo.json` | Dados brutos em JSON |

---

## 🖼 Exemplo de saída

```
==================================================
   🌤  g-clima — Relatório do Clima
==================================================

📍 Cidades disponíveis:
   1. São Paulo
   2. Rio de Janeiro
   ...

📊 Estatísticas dos últimos 7 dias:
   🌡  Mínima : 18.3°C
   🌡  Máxima : 31.7°C
   🌡  Média  : 24.5°C

✅ Gráfico salvo em:  clima_sao_paulo.png
✅ Dados JSON salvos: clima_sao_paulo.json

🎉 Relatório gerado com sucesso!
```

---

## 🛠 Tecnologias

- **Python 3.8+**
- [Open-Meteo API](https://open-meteo.com/) — dados climáticos gratuitos
- [Matplotlib](https://matplotlib.org/) — geração de gráficos

---

## 📄 Licença

MIT — fique à vontade para usar, modificar e distribuir.
