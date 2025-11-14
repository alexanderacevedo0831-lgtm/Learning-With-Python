def main():
    word = input("Input: ")
    print(f"Output: {shorten(word)}")

    
def shorten(word: str) -> str:
    # Removes all vowels ( A, E, I, O, U ) from the input string
    if not isinstance(word, str):
        raise TypeError("Input must be a string")
        
    vowels = "aeiouAEIOU"
    return "".join([char for char in word if char not in vowels])
        
if __name__ == "__main__":
    main()