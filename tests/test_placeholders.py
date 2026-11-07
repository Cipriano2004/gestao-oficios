from app.services.placeholders import DadosPlaceholder, formatar_endereco, processar_placeholders


def test_substitui_endereco_basico():
    d = DadosPlaceholder(endereco="Rua A", numero_endereco="10", bairro="Centro")
    texto = "Na [ENDEREÇO], nº [NÚMERO] - [BAIRRO]."
    assert processar_placeholders(texto, d) == "Na Rua A, nº 10 - Centro."


def test_endereco_formatado_com_e_sem_underscore():
    d = DadosPlaceholder(endereco="Rua A", numero_endereco="10", bairro="Centro")
    assert processar_placeholders("[ENDERECO_FORMATADO]|[ENDERECOFORMATADO]", d) == \
        "Rua A, 10 - Centro|Rua A, 10 - Centro"


def test_formatar_endereco_parcial():
    assert formatar_endereco("Rua A", "", "Centro") == "Rua A - Centro"
    assert formatar_endereco("", "", "Centro") == "Centro"
    assert formatar_endereco("", "", "") == ""


def test_em_frente_ausente_remove_trecho():
    d = DadosPlaceholder(endereco="Rua A")
    assert processar_placeholders("Na [ENDEREÇO] em frente a [EM_FRENTE].", d) == "Na Rua A."


def test_em_frente_preenche_tambem_horario():
    d = DadosPlaceholder(em_frente="das 9h às 17h")
    assert processar_placeholders("[EM_FRENTE] / [HORARIO]", d) == "das 9h às 17h / das 9h às 17h"


def test_municipe_e_telefone():
    d = DadosPlaceholder(municipe_tratamento="Sr.", municipe_nome="José",
                         municipe_telefone=" (11) 9999-0000 ")
    texto = "[MUNICIPE_TRATAMENTO] [MUNICIPENOME] tel [MUNICIPE_TEL] [TELEFONE]"
    assert processar_placeholders(texto, d) == "Sr. José tel (11) 9999-0000 (11) 9999-0000"


def test_evento():
    d = DadosPlaceholder(data_evento="15/12", hora_inicio="9h", hora_fim="12h",
                         numero_inicio="1", numero_fim="99")
    texto = "[DATA_EVENTO] [HORA_INICIO]-[HORA_FIM] nº [NUMERO_INICIO] a [NUMERO_FIM]"
    assert processar_placeholders(texto, d) == "15/12 9h-12h nº 1 a 99"


def test_texto_vazio_retorna_igual():
    assert processar_placeholders("", DadosPlaceholder()) == ""
    assert processar_placeholders(None, DadosPlaceholder()) is None


def test_de_dict_ignora_campos_extras_e_faz_strip():
    d = DadosPlaceholder.de_dict({"endereco": "  Rua B ", "outro": "x"})
    assert d.endereco == "Rua B"
    assert d.bairro == ""
