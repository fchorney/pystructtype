{{obj.name}}
{{obj.name|length * "="}}

.. automodule:: {{obj.name}}{%- block subpackages %}
{%- if obj.subpackages %}

Subpackages
-----------

.. toctree::
   :titlesonly:
   :maxdepth: 1
{% for subpackage in obj.subpackages %}
   {% if subpackage.display %}{{ subpackage.short_name }}/index.rst{% endif -%}
{%- endfor %}
{%- endif %}{%- endblock -%}{%- block submodules %}
{%- if obj.submodules %}

Submodules
----------

.. toctree::
   :titlesonly:
   :maxdepth: 1
{% for submodule in obj.submodules %}
   {% if submodule.display %}{{ submodule.short_name }}/index.rst{% endif -%}
{%- endfor %}
{%- endif %}{%- endblock -%}
