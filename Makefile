CFLAGS ?= -Wall -Werror -g
LDFLAGS ?=

PROG := su-exec
SRCS := $(PROG).c

all: $(PROG)

$(PROG): $(SRCS)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

$(PROG)-static: $(SRCS)
	$(CC) $(CFLAGS) -o $@ $^ -static $(LDFLAGS)

test:
	./tests/test-container.sh

clean:
	rm -f $(PROG) $(PROG)-static

# Build using Makefile (recommended)
# make build
# make build-multi  # for multi-architecture

# Run tests
# make test
# ./tests/test-container.sh.sh
