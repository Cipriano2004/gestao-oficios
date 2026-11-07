"""Secretarias e modelos de ofício padrão (textos genéricos, sem dados pessoais)."""

from ..extensions import db
from ..models import Departamento, TemplateOficio

SECRETARIAS = [
    ("GAB", "Gabinete do Prefeito"),
    ("SADS", "Secretaria de Assistência e Desenvolvimento Social"),
    ("SCT", "Secretaria de Cultura e Turismo"),
    ("SME", "Secretaria de Educação"),
    ("SMMA", "Secretaria de Meio Ambiente"),
    ("SOP", "Secretaria de Obras Públicas"),
    ("SS", "Secretaria de Segurança"),
    ("SSU", "Secretaria de Serviços Urbanos"),
    ("ST", "Secretaria de Transportes"),
]

_FECHO = ("Contando com a compreensão e colaboração, para providências, e certo do pronto "
          "atendimento a esta solicitação, renovamos os votos de elevada estima e consideração.")
_IN_LOCO = ('Considerando que, após visita "in loco", constatei a veracidade da justa '
            "reivindicação, solicitamos assim uma ação do Poder Executivo com a maior "
            "brevidade possível.")

MODELOS = [
    ("SMMA", "Poda de Árvore",
     "Solicita poda de árvore na [ENDEREÇO], nº [NÚMERO] - [BAIRRO].",
     "Munícipes reivindicam esta solicitação, em face de a(s) árvore(s) existente(s) no endereço "
     "acima referido encontrar(em)-se com galhos avançando sobre a via e/ou sobre a rede elétrica, "
     "oferecendo risco à integridade física de pedestres, veículos e imóveis do entorno.\n\n"
     "Diante do exposto, solicitamos a realização de vistoria e a execução da poda necessária, de "
     "forma a restabelecer a segurança no local e evitar danos materiais e pessoais."),
    ("SMMA", "Supressão de Árvore",
     "Solicita análise para supressão de árvore na [ENDEREÇO], nº [NÚMERO] - [BAIRRO].",
     "Munícipes reivindicam esta solicitação, em virtude de a árvore localizada no endereço acima "
     "apresentar risco iminente de queda, com tronco ou raízes comprometidas, podendo causar "
     "acidentes graves a pedestres, veículos e imóveis vizinhos.\n\n"
     "Dessa forma, solicitamos vistoria técnica e, se constatada a necessidade, a supressão da "
     "referida árvore, bem como as devidas orientações quanto ao plantio de nova muda, se cabível."),
    ("SSU", "Tapa Buraco",
     "Solicita operação tapa buraco na [ENDEREÇO], nº [NÚMERO] - [BAIRRO].",
     "Munícipes reivindicam esta solicitação, tendo em vista a existência de buracos na via "
     "supracitada, que vêm causando transtornos aos motoristas e pedestres, podendo inclusive "
     "ocasionar acidentes e danos materiais aos veículos.\n\n"
     "Nesse sentido, solicitamos a realização de vistoria e a execução de operação tapa buraco no "
     "trecho mencionado, visando garantir melhores condições de tráfego e segurança a todos."),
    ("SSU", "Limpeza, Capinação e Roçagem",
     "Operação de capinação e limpeza na [ENDEREÇO], nº [NÚMERO] - [BAIRRO].",
     "Tal solicitação provém do fato de que este vereador foi procurado pelos munícipes que por ali "
     "residem e trabalham, os quais solicitam tal benefício.\n\n" + _IN_LOCO + "\n\n"
     "Mesclando a importância da situação objeto, requer-se que a Secretaria Municipal de Serviços "
     "Urbanos realize os procedimentos necessários."),
    ("SSU", "Substituição de Lâmpada",
     "Substituição de lâmpada de iluminação pública na [ENDEREÇO], nº [NÚMERO] - [BAIRRO].",
     "Munícipes reivindicam esta solicitação, em razão de pontos de iluminação pública apagados ou "
     "com oscilações de intensidade na via mencionada, o que vem deixando o local pouco iluminado "
     "durante o período noturno, aumentando a sensação de insegurança e o risco de ocorrências.\n\n"
     "Diante do exposto, solicitamos a substituição das lâmpadas queimadas e a verificação da rede "
     "de iluminação pública no endereço acima, a fim de restabelecer a adequada luminosidade e "
     "garantir maior segurança aos moradores e transeuntes."),
    ("SSU", "Manutenção de Boca de Lobo",
     "Manutenção, limpeza e desobstrução da caixa coletora (boca de lobo) na [ENDEREÇO], "
     "nº [NÚMERO] - [BAIRRO].",
     "Considerando que a solicitação se faz necessária em face de recebermos constantes "
     "solicitações e queixas dos moradores e munícipes que passam pelo local; e que, em dias de "
     "chuva, as caixas entupidas têm dificultado o escoamento da água, trazendo riscos à saúde de "
     "quem trafega pela via.\n\n" + _IN_LOCO + "\n\n" + _FECHO),
    ("SSU", "Manutenção de Calçada",
     "Manutenção da via de pedestres (calçada) na [ENDEREÇO], nº [NÚMERO] - [BAIRRO].",
     "Considerando as constantes queixas dos moradores e munícipes que passam pelo local, "
     "em razão de danos e desníveis na calçada que dificultam a passagem e trazem risco de queda e "
     "à integridade física dos pedestres.\n\n" + _IN_LOCO + "\n\n" + _FECHO),
    ("SSU", "Nivelamento e Manutenção de Via",
     "Solicitação de nivelamento e manutenção da via na [ENDEREÇO] – [BAIRRO].",
     "Considerando o estado atual do leito carroçável da [ENDEREÇO], que apresenta irregularidades "
     "e desníveis acentuados, dificultando o tráfego de veículos e o acesso dos moradores às suas "
     "residências;\n\n"
     "Considerando que o nivelamento da via é fundamental para evitar o acúmulo de águas pluviais e "
     "garantir a segurança e o bem-estar de todos que utilizam esse logradouro público;\n\n" + _FECHO),
    ("SOP", "Estudo Técnico de Drenagem",
     "Solicitação de estudo técnico para drenagem e escoamento de águas pluviais na [ENDEREÇO] – "
     "[BAIRRO].",
     "Considerando os relatos de alagamentos recorrentes na [ENDEREÇO], especialmente em dias de "
     "chuva forte, causando transtornos e prejuízos aos moradores;\n\n"
     "Solicitamos a realização de estudo técnico para avaliar a implantação ou adequação do sistema "
     "de drenagem e escoamento de águas pluviais no local.\n\n" + _FECHO),
    ("ST", "Fechamento de Rua (Evento)",
     "Autorização para fechamento parcial da via na [ENDEREÇO] - [BAIRRO], dia [DATA_EVENTO], "
     "[HORARIO].",
     "Venho pelo presente solicitar a Vossa Excelência autorização para fechamento parcial da via "
     "na [ENDEREÇO] - [BAIRRO], dia [DATA_EVENTO], [HORARIO], para a realização de ação social.\n\n"
     "Em prol da população, faço o apelo para que avaliem a solicitação feita.\n\n"
     "Contando com o apoio e atendimento por parte dos órgãos responsáveis, antecipamos "
     "agradecimentos."),
    ("ST", "Redutor de Velocidade (Lombada)",
     "Estudos para implantação de redutor de velocidade (lombada) na [ENDEREÇO], nº [NÚMERO] - "
     "[BAIRRO].",
     "Munícipes reivindicam esta solicitação em razão do intenso fluxo de veículos e da alta "
     "velocidade praticada por alguns condutores no trecho citado, o que vem colocando em risco a "
     "integridade física de pedestres, crianças, idosos e demais usuários da via.\n\n"
     "Diante desse cenário, solicitamos estudos técnicos para a implantação de redutor de "
     "velocidade (lombada) e da devida sinalização horizontal e vertical."),
    ("ST", "Faixa de Pedestre",
     "Estudo para criação e pintura de faixa de pedestre na [ENDEREÇO], nº [NÚMERO] - [BAIRRO].",
     "Munícipes vêm reivindicando a implantação e pintura de faixa de pedestre no endereço acima, "
     "em razão do intenso fluxo de pedestres e do risco à travessia segura no local.\n\n"
     "Diante do exposto, solicitamos a realização de estudo técnico para avaliar a viabilidade da "
     "implantação, bem como de sinalização complementar, quando necessário.\n\n" + _FECHO),
    ("ST", "Manutenção de Ponto de Ônibus",
     "Reforma, manutenção e cobertura do ponto de ônibus na [ENDEREÇO], nº [NÚMERO] – [BAIRRO].",
     "Atendendo às reivindicações dos usuários do transporte coletivo, solicitamos providências "
     "para a reforma e manutenção do ponto de ônibus localizado no endereço acima.\n\n"
     "As condições precárias do local vêm gerando desconforto e insegurança aos passageiros, "
     "sobretudo idosos e estudantes, expostos ao sol e à chuva.\n\n" + _FECHO),
    ("SS", "Intensificação de Patrulhamento",
     "Solicitação de intensificação de patrulhamento na [ENDEREÇO] – [BAIRRO].",
     "Considerando os relatos de insegurança por parte dos moradores da [ENDEREÇO], especialmente "
     "nas proximidades do nº [NÚMERO];\n\n"
     "Considerando a importância da atuação da Guarda Civil Municipal no patrulhamento preventivo e "
     "comunitário para garantir a segurança dos cidadãos;\n\n" + _FECHO),
    ("SS", "Apoio de Segurança (Evento)",
     "Solicitação de apoio de segurança na [ENDEREÇO] - [BAIRRO], dia [DATA_EVENTO], [HORARIO].",
     "Venho pelo presente solicitar a Vossa Excelência apoio de segurança, através da Guarda "
     "Municipal, na [ENDEREÇO] - [BAIRRO], dia [DATA_EVENTO], [HORARIO], durante ação social "
     "voltada à comunidade.\n\n"
     "Contando com o apoio e atendimento por parte dos órgãos responsáveis, antecipamos "
     "agradecimentos."),
    ("SADS", "Cesta Básica",
     "Encaminhamento para atendimento técnico social - Cesta Básica",
     "Venho por meio deste ofício encaminhar a solicitação de atendimento técnico social para "
     "avaliação e, se cabível, concessão de benefício alimentar (cesta básica) à munícipe "
     "[MUNICIPE_TRATAMENTO] [MUNICIPE_NOME], residente na [ENDEREÇO], nº [NÚMERO] - [BAIRRO], neste "
     "Município.\n\n"
     "A presente demanda decorre de situação de vulnerabilidade social relatada, motivo pelo qual "
     "se faz necessária a análise da equipe técnica dessa Secretaria.\n\n"
     "Coloco-me à disposição para quaisquer esclarecimentos e renovo os votos de elevada estima e "
     "consideração."),
]


def garantir_secretarias() -> dict[str, Departamento]:
    existentes = {d.sigla: d for d in Departamento.query.all()}
    for sigla, nome in SECRETARIAS:
        if sigla not in existentes:
            dep = Departamento(sigla=sigla, nome=nome)
            db.session.add(dep)
            existentes[sigla] = dep
    db.session.commit()
    return existentes


def recriar_modelos() -> int:
    """Apaga e recria os modelos padrão. Retorna quantos foram criados."""
    deps = garantir_secretarias()
    TemplateOficio.query.delete()
    criados = 0
    for sigla, titulo, assunto, corpo in MODELOS:
        dep = deps.get(sigla)
        if dep:
            db.session.add(TemplateOficio(titulo=titulo, assunto=assunto, corpo_texto=corpo,
                                          departamento_id=dep.id))
            criados += 1
    db.session.commit()
    return criados
