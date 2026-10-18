<div align="center">

# 🦉 A.T.E.N.A — v2

### Assistente pessoal de IA por voz para Windows — em português do Brasil

*Nomeada em homenagem a Atena, deusa grega da sabedoria*

**Criada por Felipe Casale** · Baseada no projeto [Mark-LVI](https://github.com/FatihMakes/Mark-LVI) de **FatihMakes**

![Versão](https://img.shields.io/badge/vers%C3%A3o-2.0-gold)
![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-3776AB?logo=python&logoColor=white)
![Windows](https://img.shields.io/badge/Windows-10%20%7C%2011-0078D6?logo=windows&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini-Live%20API-8E75B2?logo=googlegemini&logoColor=white)
![Idioma](https://img.shields.io/badge/idioma-pt--BR-009C3B)
![Licença](https://img.shields.io/badge/licen%C3%A7a-CC%20BY--NC%204.0-lightgrey)

</div>

---

## ✨ O que é a ATENA

A **ATENA** é uma assistente de voz que roda no seu computador. Ela conversa em tempo real, **controla o PC**, organiza o seu dia e tem personalidade própria: um mordomo digital educado, leal e de **humor seco e afiado**.

Ela fica no ícone ao lado do relógio do Windows, **dormindo e ouvindo só o próprio nome**. Basta dizer **"Atena"** para ela acordar, ou "Atena, …" com o pedido inteiro de uma vez.

> 💬 *"Atena, abre a pasta Provas no disco D."*
> 💬 *"Me lembra de tirar a pizza do forno daqui a 20 minutos."*
> 💬 *"Anota que dia 25 vou ao dentista às 14h."*
> 💬 *"Como está o PC?"*
> 💬 *"Modo jogo."*
> 💬 *"Escreve um e-mail pro professor João perguntando sobre a prova."*
> 💬 *"Só isso, Atena."*

---

## 🏛️ Por que "Atena"?

O nome foi escolhido por seu criador, **Felipe Casale**, em homenagem a **Atena**, a deusa grega da **sabedoria**, da estratégia e da razão. Filha de Zeus, ela nasceu da cabeça do pai já adulta e armada. Era a protetora de Atenas, cidade que leva o seu nome e onde o **Partenon** foi construído em sua honra. Seu símbolo é a **coruja**, por isso a coruja está nos HUDs da assistente. Ela também era chamada de **Palas Atena**.

---

## 🚀 Recursos principais

| | Recurso | Descrição |
|---|---|---|
| 🎙️ | **Conversa por voz em tempo real** | Gemini Live API: baixa latência e conversas longas |
| 🎩 | **Personalidade de mordomo espirituoso** | Educada, sempre "senhor", com sarcasmo sutil e ironia; fica séria quando o assunto pede |
| 🇧🇷 | **Português por padrão** | Inicia sempre em pt-BR e fala de si mesma no feminino |
| 👂 | **Palavra de ativação "Atena"** | Offline (Vosk). Em segundo plano **não ouve nada além do nome** |
| 🦉 | **5 estilos de HUD** | Esfera Neural, Emblema de Atena, **Coruja 3D esculpida**, Rosto e Núcleo |
| 😊 | **Humor da coruja** | Reage a elogios, "boa noite" e "bom dia", e dorme de verdade à noite |
| 🌙 | **Modo noturno automático** | Das 23h às 6h fala mais baixo e escurece o HUD |
| ⏰ | **Lembretes falados** | "daqui a 20 min", "às 18h", "a cada 1 hora" |
| 📅 | **Agenda** | Anota compromissos por dia, avisa no cumprimento e 30 min antes |
| 📊 | **Resumo do dia** | Quanto tempo você passou em cada programa e o que ela fez |
| 🖥️ | **Status do PC** | Temperatura e uso de CPU/GPU, RAM e tempo ligado (inclui AMD) |
| 🎮 | **Modo jogo** | Fecha programas pesados, silencia notificações e limpa a tela |
| 🔊 | **Fone ↔ caixa de som** | Troca a saída de áudio por voz e acompanha as trocas do Windows |
| ✉️ | **E-mails** | Escreve e deixa o rascunho pronto no Gmail (Brave). Quem envia é você |
| 🗂️ | **Arquivos e pastas** | Cria e abre pastas em **qualquer disco**, encontrando-as **pelo nome** na hora |
| 🧩 | **Plugins** | Claude, Brave, Steam (abre jogos pelo nome), VS Code, Git Bash, desligar o PC… |
| 🌤️ | **Clima real** | Agora e previsão de 7 dias (Open-Meteo) |
| 🗣️ | **17 vozes** | Incluindo 12 femininas: Laomedeia, Despina, Sulafat, Gacrux… |

---

## 🆕 Novidades da versão 2

### 🎩 Personalidade e conversa
- **Personalidade completamente reescrita**, no estilo de um assistente-mordomo britânico:
  - impecavelmente educada e leal;
  - **humor seco por contraste**: cortesia perfeita por fora, ironia sutil por dentro;
  - comenta a situação (o horário, você abrindo a Steam pela 4ª vez);
  - entra na brincadeira e varia as falas;
  - fica calma e séria em assuntos sérios.
- **Abertura inteligente:**
  - *"Bem-vindo, senhor."* + hora, data, temperatura e **compromissos do dia**;
  - a partir da 3ª abertura do dia, apenas *"Bem-vindo de volta, senhor."*

### 👂 Segundo plano de verdade
- Ao clicar no X, minimizar ou dizer **"Só isso, Atena"**, ela **dorme** e não ouve mais nada além do próprio nome. Isso vale mesmo com o botão WAKE WORD desligado.
- **"Atena, abre a Steam"** funciona dito de uma vez: o áudio dos últimos segundos é enviado junto com o nome.
- Detecção do nome **muito mais precisa**: só frases completas, nome no início e alta confiança. Acabaram os falsos acionamentos.
- Ao ser chamada pelo nome, a janela abre e ela volta a dormir **20 s depois** da conversa.
- O auto-start abre a ATENA **já dormindo** no ícone.

### 😊 Humor da coruja e modo noturno
- **Elogios**: olhos sorrindo (^ ^), corações e brilhos; a coruja 3D bate as asas de alegria.
- **"Boa noite, Atena"**: fecha os olhos devagar, solta "z", recolhe as asas e vai dormir.
- **"Bom dia, Atena"**: acorda animada.
- **Modo noturno (23h–6h)**: voz a 25% do volume, HUD escurecido e coruja sonolenta. Os horários são configuráveis.

### 🦉 Coruja 3D esculpida
- Refeita com **cerca de 550 penas 3D sólidas**, com luz e sombra: disco facial em coração, asas em camadas, garras douradas num galho de oliveira.
- **Sem interação com o mouse.** Ela olha em volta sozinha, se espreguiça, vira para você quando você fala, inclina a cabeça ao pensar e bate as asas ao falar.

### ⏰ Lembretes, 📅 agenda e 📊 resumo do dia
- **Lembretes falados**: relativos ("daqui a 2 horas"), em horário fixo ("às 18h") e repetidos ("a cada 1 hora"). Ela fala o lembrete mesmo em segundo plano, mostra uma notificação e guarda tudo entre reinícios.
- **Agenda**:
  - "anota que dia 25 vou ao dentista às 14h";
  - "o que tenho essa semana?";
  - lembrete automático 30 min antes;
  - menção no cumprimento do dia.
- **Resumo do dia**: tempo ativo, tempo por programa (sem contar o tempo longe do PC) e o que a ATENA fez. O registro é apagado depois do resumo da noite, e nada sai do PC.

### 🖥️ PC e sistema
- **Status do PC**: temperatura **e uso** da CPU e da GPU, RAM e tempo ligado. Lê sensores AMD/Intel/NVIDIA pelo LibreHardwareMonitor e, sem ele, o uso da GPU pelos contadores do Windows.
- **Modo jogo / modo normal**: fecha navegadores, VS Code, Claude e Office, silencia notificações, desliga a luz noturna e deixa a área de trabalho limpa. "Modo normal" desfaz.
- **Saída de áudio por voz**: "coloca o som no fone" e "na caixa de som". A ATENA também **segue automaticamente** a saída escolhida no Windows.
- **Desligar ou reiniciar o PC** por voz, com **30 s de contagem** e "cancelar".
- **Correções de áudio**: buffer de saída maior, checagens fora da fala e Coruja 3D mais leve durante a fala. Isso acabou com os cortes na voz.

### ✉️ E-mails e 🧩 novos plugins
- **E-mails**: ela escreve a mensagem e o assunto e abre o rascunho no **Gmail, no Brave**. **Nunca envia sozinha.** Os contatos ficam num arquivo de texto simples (`config/contatos.txt`), editável à mão.
- **Git Bash**: "abrir o Git" ou "abrir o Git na pasta X no disco D".

---

## 📜 Recursos da versão 1 (em relação ao projeto original)

<details>
<summary><b>Clique para ver</b></summary>

- **HUDs novos:**
  - 🌐 **Esfera Neural**: globo 3D de circuitos;
  - 🦉 **Emblema de Atena**: coruja, louros, faixa ΑΘΗΝΑ • ΣΟΦΙΑ • ΠΑΛΛΑΣ e borda grega.
- **Identidade:** renomeada de JARVIS para **ATENA** em toda a interface; português do Brasil por padrão; respostas sobre a própria origem.
- **Clima real** (Open-Meteo) com cidade padrão salva (São Carlos, SP).
- **Palavra de ativação "Atena"** (Vosk, offline), no lugar de "Hey Jarvis".
- **Segundo plano:**
  - bandeja do sistema, com auto-start direto no ícone;
  - instância única;
  - atalho **Ctrl + Alt + A**.
- **Comandos de controle:**
  - **"Encerrar Atena"** fecha o programa com despedida;
  - gatilhos de fechar e desligar separados.
- **Arquivos:**
  - acesso a todos os discos;
  - **índice de pastas** para achar qualquer pasta pelo nome na hora;
  - ação **abrir** para pastas e arquivos.
- **Plugins:** Claude, Brave (com site), Steam (inicia jogos instalados pelo nome) e VS Code (abre numa pasta).
- **17 vozes Gemini** no seletor.
- **Voz RVC** experimental (DirectML/AMD), desligada por padrão.

</details>

---

## 🛠️ Instalação

### Requisitos
| Item | Versão / observação |
|---|---|
| **Sistema** | Windows 10 ou 11 |
| **Python** | 3.11, 3.12 ou 3.13 |
| **Chave de API** | Chave **gratuita** do Gemini ([Google AI Studio](https://aistudio.google.com/)) |
| **Microfone** | Qualquer um. Um **viva-voz USB** com cancelamento de eco é o ideal |
| **Opcional** | [LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor) aberto em segundo plano, para as temperaturas de CPU/GPU AMD |
| **Opcional** | Git for Windows (plugin do Git), Brave, Steam, VS Code |

### Passo a passo
```bash
git clone https://github.com/<Fcasale-dev>/https://github.com/Fcasale-dev/Atena-I.git
cd <seu-repositorio>
python setup.py      # instala as dependências do seu sistema
python main.py       # inicia a ATENA
```

1. Na primeira vez, cole sua **chave do Gemini**. Ela fica salva em `config/api_keys.json`, que **não vai para o Git**.
2. Em **🎛 CONTROLS → WAKE WORD**, instale a palavra de ativação "Atena" (download único de ~31 MB).
3. Em **⚙ SETUP**:
   - crie o **atalho na área de trabalho** (com Ctrl + Alt + A);
   - ative o **auto-start**;
   - deixe a saída de áudio em **"System default"**;
   - escolha sua voz e sua cor.
4. *(Opcional)* Em `config/contatos.txt`, adicione os contatos de e-mail, um por linha: `Nome = email`.

---

## 🎤 Guia rápido de comandos

| Você diz | A ATENA… |
|---|---|
| **"Atena"** / "Atena, …" | acorda (e já faz o pedido) |
| **"Só isso, Atena"** | volta a dormir no ícone |
| **"Encerrar Atena"** | fecha o programa |
| "Que horas são?" / "Como está o tempo essa semana?" | responde |
| "**Como está o PC?**" | temperatura e uso de CPU/GPU, RAM e tempo ligado |
| "**Modo jogo**" / "**Modo normal**" | prepara o PC para jogar / desfaz |
| "Coloca o som **no fone**" / "**na caixa de som**" | troca a saída de áudio |
| "Me lembra de X **daqui a 20 minutos**" / "**às 18h**" / "**a cada 1 hora**" | cria um lembrete falado |
| "Anota que **dia 25** vou ao dentista às 14h" / "O que tenho amanhã?" | agenda |
| "**Como foi meu dia?**" | resumo do dia |
| "Escreve um e-mail pra Ana dizendo …" | rascunho pronto no Brave |
| "Abra a pasta Provas no disco D" / "Crie uma pasta X dentro de Y" | arquivos e pastas |
| "Abrir **Claude / Brave / Steam / VS Code / Git**" / "Abre o Counter-Strike" | abre o programa ou jogo |
| "**Desligar PC**" → "Cancelar" | desliga em 30 s, ou cancela |
| "Você é incrível, Atena" / "**Boa noite, Atena**" | a coruja reage |

---

## 📁 Estrutura do projeto (principais arquivos)

```
├── main.py                    # Núcleo: sessão Gemini Live, áudio, ferramentas, segundo plano
├── ui.py                      # Interface Qt, HUDs, bandeja, modo noturno, notificações
├── core/
│   ├── prompt.txt             # Personalidade, idioma e origem
│   ├── sphere.py              # HUD Esfera Neural
│   ├── athena_hud.py          # HUD ATENA + humor/sono da coruja
│   ├── athena_owl3d.py        # HUD Coruja 3D esculpida
│   ├── wake_word.py           # Palavra de ativação "Atena" (Vosk)
│   ├── weather.py             # Clima real (Open-Meteo)
│   ├── hw_sensors.py          # Sensores de CPU/GPU (LibreHardwareMonitor)
│   ├── activity.py            # Registro local para o resumo do dia
│   ├── agenda.py              # Armazenamento da agenda
│   └── rvc_voice.py           # Voz RVC (experimental)
├── actions/
│   ├── file_controller.py     # Arquivos: todos os discos, índice de pastas, abrir
│   ├── system_monitor.py      # Métricas do sistema
│   └── weather_report.py      # Clima
├── plugins/
│   ├── abrir_claude.py · abrir_brave.py · abrir_steam.py · abrir_vscode.py · abrir_git.py
│   ├── modo_jogo.py · status_pc.py · saida_audio.py · desligar_pc.py
│   ├── lembretes.py · agenda.py · resumo_dia.py · escrever_email.py · humor.py
├── voice_engine/rvc_server.py # Servidor RVC (opcional)
└── config/                    # Chave, contatos, agenda, lembretes, registros (fora do Git)
```

---

## 🔐 Privacidade

- **Ficam fora do repositório**, pelo `.gitignore`:
  - a chave de API e os certificados;
  - a memória, os **contatos**, a **agenda**, os **lembretes** e o **registro de uso**;
  - os modelos baixados.
- A palavra de ativação roda **100% offline**. Em segundo plano, a ATENA **não envia áudio** para lugar nenhum até ouvir o nome.
- O resumo do dia guarda **só o nome dos programas**, nunca o título das janelas, e é apagado depois do resumo da noite.
- E-mails **nunca são enviados automaticamente**. Desligar o PC tem **contagem de 30 s com cancelamento**.

---

## 🙏 Créditos

- **[FatihMakes](https://github.com/FatihMakes)**, criador do **[Mark-LVI](https://github.com/FatihMakes/Mark-LVI)**, a **base da ATENA**. A arquitetura original vem do trabalho dele: sessão Gemini Live, sistema de ações e plugins, avatar, memória, painel remoto e muito mais. Muito obrigado! 💙
- **Felipe Casale**: identidade ATENA, personalidade, HUDs, plugins e todas as melhorias das versões 1 e 2.
- [Google Gemini](https://ai.google.dev/), voz e linguagem.
- [Open-Meteo](https://open-meteo.com/), clima.
- [Vosk / Alpha Cephei](https://alphacephei.com/vosk/), reconhecimento de voz offline (Apache 2.0).
- [LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor), sensores de hardware (MPL 2.0).
- [MediaPipe](https://github.com/google-ai-edge/mediapipe), modelo facial do avatar (Apache 2.0).
- [RVC-Project](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI), conversão de voz (opcional).

---

## ⚖️ Licença

Distribuída sob a licença **[Creative Commons Atribuição-NãoComercial 4.0 (CC BY-NC 4.0)](https://creativecommons.org/licenses/by-nc/4.0/)**, a mesma do projeto original.

- ✅ Você pode usar, copiar, modificar e compartilhar.
- ✅ Você deve dar os **créditos** a **Felipe Casale** (ATENA) e a **FatihMakes** (Mark-LVI) e indicar o que modificou.
- ❌ **Uso comercial não é permitido.**

Veja o arquivo [`LICENSE`](LICENSE) para o texto completo.

<div align="center">

---

*Feito com 🦉 por **Felipe Casale** · São Carlos, SP — Brasil*

</div>
