# Word Counter Tool Tests

## Tool description:
**Description:** This tool counts the number of words in a given text input.

**Input:**
- text (str): The input text to be processed.

**Output:**
- word_count (int): The number of words in the input text.

## Test cases:

### 🤖 test_word_counter_empty_string
**Description:** Tests the behavior when an empty string is provided as input.  
**Expected Behavior:** Should return "Word count: 0"

### 🤖 test_word_counter_single_word
**Description:** Tests the behavior when a single word is provided as input.  
**Expected Behavior:** Should return "Word count: 1"

### 🤖 test_word_counter_multiple_words
**Description:** Tests the behavior when a normal sentence with multiple words is provided.  
**Expected Behavior:** Should return "Word count: 4" for the input "This is four words"

### 🤖 test_word_counter_with_extra_spaces
**Description:** Tests the behavior when text contains multiple spaces between words.  
**Expected Behavior:** Should correctly count words by ignoring extra whitespace. Returns "Word count: 3" for input "   Too    many   spaces   "

### 🤖 test_input_schema_validation
**Description:** Tests the input schema validation using WordCounterInput class.  
**Expected Behavior:** Should successfully validate and store valid text input.

### 🤖 test_tool_name
**Description:** Verifies the tool's name property.  
**Expected Behavior:** Should return 'Word Counter Tool'

### 🤖 test_tool_description
**Description:** Verifies the tool's description property.  
**Expected Behavior:** Should return 'Counts the number of words in a given text.'

### 🤖 test_tool_args_schema
**Description:** Verifies the tool's input model schema configuration.  
**Expected Behavior:** Should verify that:
- The input_model exists
- It is a subclass of WordCounterInput
- It contains the required 'text' field