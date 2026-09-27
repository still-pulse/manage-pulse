# ManagePulse

App Frappe/ERPNext para **pesquisas de satisfação** multi-unidade (paciente, acompanhante e visitante).

Repositório: [still-pulse/manage-pulse](https://github.com/still-pulse/manage-pulse)

## Escopo (Fase 1)

- DocTypes em **PT-BR** no Desk
- **Modelo de Pesquisa** com perguntas por seção/critério
- Filtro **Aplicável a (unidades)**: se vazio, vale para qualquer `Company`
- **Resposta da Pesquisa** com preenchimento manual no Desk
- Escala: Ótimo · Bom · Regular · Ruim · Não Utilizou
- **NPS** 0–10 e média geral (ignora “Não Utilizou”)
- Contato opcional (nome, telefone, acompanhante)
- Seed dos modelos:
  - `PESQUISA UPA - PRONTO ATENDIMENTO`
  - `PESQUISA UPA - OBSERVAÇÃO`
- Roles: `ManagePulse Manager`, `ManagePulse Viewer`

## Página pública (Fase 2)

URL:

```
/pesquisa-satisfacao/<slug>?unidade=<Nome da Company>
```

Exemplos:

```
/pesquisa-satisfacao/upa-pronto-atendimento?unidade=UPA%20AKIRA%20-%20Beneficência%20Hospitalar%20de%20Cesário%20Lange
/pesquisa-satisfacao/upa-observacao?unidade=...
```

- Sem login (guest)
- **Pergunta 1:** quais serviços utilizou (multi-select = seções do modelo)
- Só avalia critérios dos serviços marcados (escala Ótimo / Bom / Regular / Ruim)
- NPS 0–10 + comentário opcional
- Contato opt-in (nome, telefone, acompanhante)
- Grava `servicos_utilizados` + itens filtrados; `owner` = Guest

APIs:

- `managepulse.api.public_survey.get_modelo_publico`
- `managepulse.api.public_survey.enviar_resposta`

## Dashboard e relatórios (Fase 3)

### Links no Desk (substitua `{site}` pela URL do ERPNext)

| O quê | Rota |
|-------|------|
| **Workspace Gestor** (atalhos da pesquisa) | `https://{site}/app/gestor` |
| **Dashboard** | `https://{site}/app/dashboard-view/ManagePulse` |
| **Análise de Satisfação** | `https://{site}/app/query-report/Analise%20de%20Satisfacao` |
| **Satisfação por Critério** | `https://{site}/app/query-report/Satisfacao%20por%20Criterio` |
| Lista de respostas | `https://{site}/app/resposta-da-pesquisa` |

Também no Awesomebar: digite `ManagePulse`, `Analise de Satisfacao` ou `Satisfacao por Criterio`.

> **Nota:** nomes de Report sem acento de propósito — o Frappe monta o path Python com `scrub(nome)` e pastas com acento quebram o import.

### Relatório Análise de Satisfação (`Analise de Satisfacao`)

Filtros:

- Período (`De` / `Até`)
- Unidade (`Company`)
- Modelo de Pesquisa
- Tipo de Pesquisa
- Serviço (autocomplete a partir das seções/respostas)
- Canal / Status
- **Visão:** Respostas · Por Unidade · Por Serviço

Inclui **report summary** (total, NPS Score, NPS médio, média geral, pedidos de contato) e gráfico conforme a visão.

**NPS Score** = % promotores (9–10) − % detratores (0–6).

### Relatório Satisfação por Critério (`Satisfacao por Criterio`)

Breakdown por serviço (seção) + critério: contagem Ótimo/Bom/Regular/Ruim, % positivo e média 1–5.

### Number Cards e gráficos

Criados no migrate/install (`setup.install.ensure_dashboard_artifacts`):

- Cards: total respostas, NPS Score, média NPS, média geral, pedidos de contato
- Charts: respostas por unidade, NPS médio por unidade, série temporal, por canal
- Dashboard DocType `ManagePulse` + cards/charts no Workspace

## DocTypes

| DocType | Tipo | Função |
|---------|------|--------|
| Modelo de Pesquisa | Parent | Template (título, slug, tipo, unidades, perguntas) |
| Pergunta do Modelo | Child | Seção + critério + tipo (Escala/NPS/Texto) |
| Unidade do Modelo | Child | Link `Company` (aplicável a) |
| Resposta da Pesquisa | Parent | Submissão (Desk ou pública) |
| Item da Resposta | Child | Avaliação por critério |
| Servico Utilizado da Resposta | Child | Serviços marcados na P1 |

## Instalação

No bench (site com ERPNext):

```bash
# clone na pasta apps (nome do app Python: managepulse)
cd frappe-bench/apps
git clone https://github.com/still-pulse/manage-pulse.git managepulse

cd ..
bench get-app ./apps/managepulse   # se já clonou, ou:
# bench get-app https://github.com/still-pulse/manage-pulse --branch main

bench --site SEU_SITE install-app managepulse
bench --site SEU_SITE migrate
bench clear-cache
```

Atribua o papel **ManagePulse Manager** (ou **Viewer**) aos usuários de Qualidade/Ouvidoria.

### Atualizar site que já tem o app

```bash
cd frappe-bench
bench --site SEU_SITE migrate
bench clear-cache
# se o app estiver em desenvolvimento local:
# bench --site SEU_SITE clear-cache && bench build --app managepulse
```

Depois abra:

```
https://SEU_SITE/app/gestor
https://SEU_SITE/app/query-report/Analise%20de%20Satisfacao
```

Naming das respostas: `MPS-YYYY-#####`.

## Uso rápido

1. **Modelo de Pesquisa** → conferir os 2 modelos seed (ou criar novos).
2. Opcional: preencher **Unidades aplicáveis**; vazio = qualquer Company.
3. **Resposta da Pesquisa** → novo → escolher modelo → unidade → serviços → notas → NPS → salvar.
4. **Workspace Gestor** → atalhos de Satisfação (modelos, respostas, relatórios, dashboard).
5. **Análise de Satisfação** → filtrar por unidade/período/serviço e alternar a visão.

## Estrutura

```
managepulse/
  managepulse/
    hooks.py
    api/
      public_survey.py
      metrics.py
    setup/
      install.py
      seed_modelos.py
    fixtures/
      role.json
      number_card.json
      dashboard_chart.json
      dashboard.json
    managepulse/
      doctype/
      report/
        analise_de_satisfacao/
        satisfacao_por_criterio/
      workspace/
    www/
      pesquisa_satisfacao.html
```

## Próximas fases

- QR / totem
- Alertas automáticos (NPS baixo / pedido de contato)
- Export agendado para diretoria

## Licença

MIT — Still Pulse / BHCL
