.PHONY : clean publish release

clean:
	rm --force --recursive build/
	rm --force --recursive dist/
	rm --force --recursive *.egg-info

publish: clean
	python setup.py sdist upload -r appfigures

release: clean
	@./release.sh
