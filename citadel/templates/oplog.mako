<%inherit file="/base.mako"/>
<%namespace name="utils" file="/utils.mako"/>

<%!
  from humanize import naturaltime
%>

<%def name="title()">OP Log</%def>

<%block name="main">

  <%call expr="utils.panel()">
    <%def name="header()">
      <h3 class="panel-title">OP Logs</h3>
    </%def>
    <table class="table">
      <thead>
        <tr>
          <th>When</th>
          <th>Who</th>
          <th>Appname</th>
          <th>Sha</th>
          <th>Action</th>
        </tr>
      </thead>
      <tbody>
        % for oplog in oplogs:
          <tr>
            <td>${ naturaltime(oplog.created) }</td>
            <td>${ oplog.user_real_name }</td>
            <td><a href="${ url_for("app.app", name=oplog.appname) }" target="_blank">${ oplog.appname }</a></td>
            <td>${ oplog.action.name }</td>
          </tr>
        % endfor
      </tbody>
    </table>
  </%call>

  ${ utils.paginator(g.start, g.limit) }

</%block>
