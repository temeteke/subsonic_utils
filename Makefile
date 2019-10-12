BINDIR := ~/bin

.PHONY: all install uninstall
all:

install: $(BINDIR)
	cp subsonic_playlist_add.py $(BINDIR)/

uninstall:
	rm $(BINDIR)/subsonic_playlist_add.py

$(BINDIR):
	mkdir $(BINDIR)
