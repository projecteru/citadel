<%inherit file="/base.mako"/>
<%namespace name="utils" file="/utils.mako"/>

<%def name="title()">User List</%def>

<%block name="main">
  <%call expr="utils.panel()">
    <%def name="header()">
      <h3 class="panel-title">Users</h3>
    </%def>
    <form class="navbar-form navbar-right" action="${ url_for('admin.users') }" role="search">
      <div class="form-group">
	<div class="input-group">
	  <input class="form-control" name="q" type="search" placeholder="搜索">
	  <span class="input-group-btn">
	    <button type="submit" class="btn"><span class="fui-search"></span></button>
	  </span>
	</div>
      </div>
    </form>

    <table class="table">
      <thead>
	<tr>
	  <th>ID</th>
	  <th>Name</th>
	  <th>Email</th>
	  <th>Realname</th>
	  <th>Privileged</th>
	</tr>
      </thead>
      <tbody>
	% for user in users:
	  <tr>
	    <td>${ user.id }</td>
	    <td><a href="${ url_for('admin.user_info', identifier=user.id) }">${ user.name }</a></td>
	    <td>${ user.email }</td>
	    <td>${ user.real_name }</td>
	    <td>${ 'YES' if user.privilege else 'NO' }</td>
	  </tr>
	% endfor
      </tbody>
    </table>
  </%call>

  ${ utils.paginator() }
</%block>
