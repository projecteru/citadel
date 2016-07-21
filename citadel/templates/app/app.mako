<%inherit file="/base.mako"/>
<%namespace name="utils" file="/utils.mako"/>

<%def name="title()">
  ${ app.name }
</%def>

<%def name="more_css()">
  .block-span { display: block; }
</%def>

<%block name="main">

  <%utils:panel>
    <%def name="header()">
      <h3 class="panel-title">App
	<a href="${ url_for('app.app_env', name=app.name) }" class="btn-xs">
	  <span class="fui-arrow-right"></span> Environment Variables
	</a>
      </h3>
    </%def>
    <h4>${ app.name }</h4>
    <br>
    <h5>这里看log</h5>
    <ul class="list-group">
      % for entry in versions[0].entrypoints.keys():
	<li class="list-group-item"><a target="_blank" href="${ url_for('app.get_app_log', name=app.name, entrypoint=entry, dt=now) }?limit=500">${ entry }</a></li>
      % endfor
    </ul>
  </%utils:panel>

  <%utils:panel>
    <%def name="header()">
      <h3 class="panel-title">Latest Versions
	<a href="#" class="btn-xs"><span class="fui-arrow-right"></span> More</a>
      </h3>
    </%def>
    ${ utils.version_list(versions, app) }
  </%utils:panel>

  <%utils:panel>
    <%def name="header()">
      <h3 class="panel-title">Online Containers: ${ len(containers) }</h3>
    </%def>
    ${ utils.container_list(containers) }
  </%utils:panel>

</%block>
