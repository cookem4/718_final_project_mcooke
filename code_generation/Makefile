# Compiler
CC = gcc

# Compiler flags
CFLAGS += -Wall -Wextra 

# Source file
SRC = main.c ntt_target.c 

# Object files
OBJ = $(SRC:.c=.o)

# Executable name
EXEC = ntt_test

# Default target
all: $(EXEC)

# Build the executable
$(EXEC): $(OBJ)
	$(CC) $(CFLAGS) -o $@ $(OBJ)

# Compile source files to object files
%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

# Clean up object files and executable
clean:
	rm -f $(OBJ) $(EXEC)

# Phony targets
.PHONY: all clean
