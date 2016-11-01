<%inherit file="/base.mako"/>
<%namespace name="utils" file="/utils.mako"/>

<%def name="title()">Permitted Users</%def>

<%block name="main">

  <%call expr="utils.panel()">
    <%def name="header()">
      <h3 class="panel-title">Permitted Users</h3>
    </%def>
    <table class="table">
      <thead>
        <tr>
          <th>UserID</th>
          <th>UserName</th>
        </tr>
      </thead>
      <tbody>
        % for user in users:
          <tr>
            <td>${ user.id }</td>
            <td>${ user.realname }</td>
          </tr>
        % endfor
      </tbody>
    </table>
  </%call>

  ${ utils.paginator(g.start, g.limit) }

</%block>
