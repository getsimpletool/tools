import pytest
from tools.word_counter import WordCounterTool, WordCounterInput

# Mark all async tests


@pytest.fixture
def word_counter():
    return WordCounterTool()


@pytest.mark.asyncio
async def test_word_counter_empty_string(word_counter):
    result = await word_counter.run({"text": ""})
    assert result[0].text == "Word count: 0"


@pytest.mark.asyncio
async def test_word_counter_single_word(word_counter):
    result = await word_counter.run({"text": "Hello"})
    assert result[0].text == "Word count: 1"


@pytest.mark.asyncio
async def test_word_counter_multiple_words(word_counter):
    result = await word_counter.run({"text": "This is four words"})
    assert result[0].text == "Word count: 4"


@pytest.mark.asyncio
async def test_word_counter_with_extra_spaces(word_counter):
    result = await word_counter.run({"text": "   Too    many   spaces   "})
    assert result[0].text == "Word count: 3"

# Non-async test without any marker


def test_input_schema_validation():
    input_schema = WordCounterInput(text='valid text')
    assert input_schema.text == 'valid text'

# Tests for tool metadata


@pytest.mark.asyncio
async def test_tool_name(word_counter):
    assert word_counter.name == 'Word Counter Tool'


@pytest.mark.asyncio
async def test_tool_description(word_counter):
    assert word_counter.description == 'Counts the number of words in a given text.'


@pytest.mark.asyncio
async def test_tool_args_schema(word_counter):
    schema = word_counter.input_model
    assert schema is not None
    assert issubclass(schema, WordCounterInput)
    assert 'text' in schema.model_fields
