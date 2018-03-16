=========
CHANGELOG
=========

1.4.2 (2018-03-16)
------------------

- Another small tweak needed to work in new moto. A key now always expects
  an ACL.


1.4.1 (2018-03-12)
------------------

- Tweak server startup to work with new moto APIs. Added test to verify app
  configuration works.


1.4.0 (2018-03-12)
------------------

- Upgraded to support `moto == 1.2.0`.


1.3.0 (2018-02-03)
------------------

- Use `flask_cors` to inject the proper access control headers. This way not
  only the handled HTTP methods will put the CORS headers in the response, but
  OPTIONS -- which is used by browsers to check the CORS settings - will also
  receive the headers.


1.2.0 (2017-05-23)
------------------

- Add support for Python 3.5, 3.6 and PyPy.


1.1.0 (2017-05-23)
------------------

- First public release.

- Switched to commuity tools: tox, Travis CI and Coveralls.io


1.0.1 (2017-05-15)
------------------

- Add Makefile to release.


1.0.0 (2017-05-15)
------------------

- Initial release.
