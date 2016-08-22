<%inherit file="/base.mako"/>
<%namespace name="utils" file="/utils.mako"/>

<%def name="title()">
Add Rule
</%def>

<%block name="main">
<%call expr="utils.panel()">
<%def name="header()">
<h3 class="panel-title">${ name } Add A Rule</h3>
</%def>

<div class="col-md-8 col-md-offset-2">
  <form class="form-horizontal" action="${url_for('loadbalance.add_rule', name=name)}" method="POST">
    <div class="form-group">
      <label class="col-sm-2 control-label" for="">Domain</label>
      <div class="col-sm-10">
        <input class="form-control" type="text" name="domain">
      </div>
    </div>
    <div class="form-group">
      <label class="col-sm-2 control-label" for="">Rule</label>
      <div class="col-sm-10">
        <input class="form-control" type="text" name="rule">
      </div>
    </div>
    <div class="form-group">
      <div class="col-sm-10 col-sm-offset-2">
        <button class="btn btn-info" type="submit"><span class="fui-plus"></span> Add</button>
      </div>
    </div>
  </form>
</div>

</%call>
</%block>
