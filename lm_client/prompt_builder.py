import os
import tiktoken


class PromptBuilder:
    def __init__(self, max_tokens: int = 32000, model: str = "gpt-4"):
        self.__components = []
        self.__sources = []
        self.__token_counts = []

        self.max_tokens = max_tokens

        # tokenizer (fallback-safe)
        try:
            self.encoder = tiktoken.encoding_for_model(model)
        except Exception:
            self.encoder = tiktoken.get_encoding("cl100k_base")

    # ----------------------------
    # TOKEN UTILITIES
    # ----------------------------
    def count_tokens(self, text: str) -> int:
        """Return token count for a string."""
        return len(self.encoder.encode(text))

    def get_total_tokens(self) -> int:
        """Return total tokens in current prompt."""
        return sum(self.__token_counts)

    # ----------------------------
    # INTERNAL HELPERS
    # ----------------------------
    def _truncate_to_fit(self, text: str) -> str:
        """Truncate text so it fits within remaining token budget."""
        current = self.get_total_tokens()
        remaining = self.max_tokens - current

        if remaining <= 0:
            return ""

        tokens = self.encoder.encode(text)

        if len(tokens) <= remaining:
            return text

        truncated_tokens = tokens[:remaining]
        return self.encoder.decode(truncated_tokens)

    # ----------------------------
    # ADD FILE
    # ----------------------------
    def add_from_file(self, file_path: str, truncate: bool = True):
        """Append file content, optionally truncated to fit token budget."""
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"The file {file_path} does not exist.")

        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()

        if truncate:
            content = self._truncate_to_fit(content)

        tokens = self.count_tokens(content)

        self.__components.append(content)
        self.__sources.append(file_path)
        self.__token_counts.append(tokens)

    # ----------------------------
    # ADD TEXT
    # ----------------------------
    def add_text(self, text: str, truncate: bool = True):
        """Append raw text, optionally truncated to fit token budget."""
        if truncate:
            text = self._truncate_to_fit(text)

        tokens = self.count_tokens(text)

        self.__components.append(text)
        self.__sources.append(text)
        self.__token_counts.append(tokens)

    # ----------------------------
    # REMOVE SOURCE
    # ----------------------------
    def remove_source(self, source):
        """Remove a source and rebuild token tracking."""
        if source in self.__sources:
            index = self.__sources.index(source)
            self.__sources.pop(index)
            self.__components.pop(index)
            self.__token_counts.pop(index)
        else:
            print(f"Source '{source}' not found.")

    # ----------------------------
    # OUTPUT
    # ----------------------------
    def get_prompt(self) -> str:
        """Return full combined prompt."""
        return "\n\n".join(self.__components)

    # ----------------------------
    # DEBUG
    # ----------------------------
    def print_sources(self):
        print(self.__sources)
