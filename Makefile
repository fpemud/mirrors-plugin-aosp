prefix=/usr

all:

clean:
	fixme

install:
	install -d -m 0755 "$(DESTDIR)/$(prefix)/lib64/mirrors/plugins"
	cp -r aosp "$(DESTDIR)/$(prefix)/lib64/mirrors"
	find "$(DESTDIR)/$(prefix)/lib64/mirrors/aosp" -type f | xargs chmod 644
	find "$(DESTDIR)/$(prefix)/lib64/mirrors/aosp" -type d | xargs chmod 755
	find "$(DESTDIR)/$(prefix)/lib64/mirrors/aosp" -name "*.py" | xargs chmod 755

uninstall:
	rm -rf "$(DESTDIR)/$(prefix)/lib64/mirrors/aosp"

.PHONY: all clean install uninstall
