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
  </%utils:panel>

  <%utils:panel>
    <%def name="header()">
      <h3 class="panel-title">Latest Versions
        <a href="#" class="btn-xs"><span class="fui-arrow-right"></span> More</a>
      </h3>
    </%def>
    ${ utils.release_list(releases, app) }
  </%utils:panel>

  <%utils:panel>
    <%def name="header()">
      <h3 class="panel-title">Online Containers: ${ len(containers) }</h3>
    </%def>
    <%utils:container_list containers="${ containers }">
      <button name="upgrade-all" class="btn btn-primary pull-left" data-toggle="modal" data-target="#upgrade-container-modal"><span class="fui-apple"></span> Upgrade Chosen</button>
      <button name="delete-all" class="btn btn-warning pull-right"><span class="fui-trash"></span> Delete Chosen</button>

    </%utils:container_list>
  </%utils:panel>

  <%call expr="utils.modal('upgrade-container-modal')">
    <%def name="header()">
      <h3 class="modal-title">Upgrade Container</h3>
    </%def>

    <form id="upgrade-container-form" class="form-horizontal" action="">
      <div class="form-group">
        <label class="col-sm-2 control-label" for="">Release</label>
        <div class="col-sm-10">
          <select name="release" class="form-control">
            % for release in releases:
              <option value="${ release.short_sha }">${ release.short_sha }</option>
            % endfor
          </select>
        </div>
      </div>
    </form>

    <%def name="footer()">
      <button class="btn btn-warning" id="close-modal" data-dismiss="modal"><span class="fui-cross"></span>Close</button>
      <button class="btn btn-info" id="upgrade-container-button"><span class="fui-apple"></span>Upgrade</button>
    </%def>
  </%call>

  <script>
    $('button[id=upgrade-container-button]').click(function(e){
    if (!$('input[name=container-id]:checked').length) {
    return;
    }
    e.preventDefault();
    var payload = [];
    var url = '/ajax/upgrade-container';
    $.each($('input[name=container-id]:checked'), function(){
    payload.push('container_id=' + $(this).val());
    });
    payload.push('release=' + $('select[name=release]').val())
    $.post(url, payload.join('&'), function(){
    location.reload();
    })
    });
  </script>

</%block>
