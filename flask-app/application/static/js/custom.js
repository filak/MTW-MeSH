// MTW custom javascript 1.6.2

$(document).ready(function(){

    $('[data-toggle="tooltip"]').tooltip()

    //$('[data-toggle="popover"]').popover();
    
    $(".modal-dialog").draggable({
        handle: ".modal-header"
    });    

    $('#descriptorTabs a.nav-link').click(function() {
        $('#flashedMessage').html('');
    });

    $('.clearFlashed').click(function() {
        $('#flashedMessage').html('');
    });

    $('#editScopeNote').on('hidden.bs.modal', function (e) {
        $(this).find('form')[0].reset();
    });

    $('#showHistoryModal').on('hidden.bs.modal', function (e) {
        $(this).find('form')[0].reset();
        $(this).find('#noteAudit').text('');
    });

    $('#editNote').on('hidden.bs.modal', function (e) {
        $(this).find('form')[0].reset();
    });

    $('#scopeNoteTrx').change(function() {
        $('#editScopeNote').find('#scopeNoteTrxChanged').attr('value', 'true');
    });

    $('#scopeNoteEng').change(function() {
        $('#editScopeNote').find('#scopeNoteEngChanged').attr('value', 'true');
    });

    $('#noteTrx').change(function() {
        $('#editNote').find('#noteTrxChanged').attr('value', 'true');
    });

    $('#editConcept-NEW').on('hidden.bs.modal', function (e) {
        $(this).find('form')[0].reset();
    });

    $('.formInputChanged').change(function() {
        var formchangedId = $(this).data('formchanged');
        $(formchangedId).attr('value', 'true');
    });

    $('.notrxToggle').change(function() {
        var isChecked = $(this).is(':checked');
        var termInputId = $(this).data('terminput');

        if (isChecked === true) {
            $(termInputId).find('input.termInput').removeAttr('required');
            $(termInputId).find('input.termInput').attr('placeholder', 'PrefTerm ...');
        } else {
            $(termInputId).find('input.termInput').attr('required','');
            $(termInputId).find('input.termInput').attr('placeholder', 'PrefTerm required ...');
        }
    });

    $('.deleteConceptButton').click(function() {
        var action =  $(this).data('form-action');
        var propose =  $(this).data('form-propose');

        if (action == 'delete' || action == 'purge') {
          var target = $(this).attr('title');
          $($.find(target+'-action')).attr('value', action);
        } else {
          var target = $(this).data('form');
        }

        $($.find(target+'-propose')).attr('value', propose);
        $($.find(target+'-form')).submit();
    });

    $('#deleteConcept').on('show.bs.modal', function(e) {
        var target = $(e.relatedTarget).data('form');
        var active = $(e.relatedTarget).data('active');

        if (active === false) {
           $(e.currentTarget).find('#target-form-purge').attr('title',target);
           $(e.currentTarget).find('#target-form-purge').show();
           $(e.currentTarget).find('#target-form').hide();
        } else {
           $(e.currentTarget).find('#target-form').attr('title',target);
           $(e.currentTarget).find('#target-form').show();
           $(e.currentTarget).find('#target-form-purge').hide();
        }

        var concept = $(e.relatedTarget).data('concept');
        $(e.currentTarget).find('#deleteConceptUi').text(concept);
    });

    $('#editNote').on('show.bs.modal', function(e) {
        var predicate = $(e.relatedTarget).data('predicate');
        var note = $(e.relatedTarget).data('note');
        var tnote = $(e.relatedTarget).data('tnote');
        var label = $(e.relatedTarget).data('label');

        $(e.currentTarget).find('#noteLabel').attr('value', label);
        $(e.currentTarget).find('#noteOriginal').attr('value', tnote);
        $(e.currentTarget).find('#notePredicate').attr('value', predicate);
        $(e.currentTarget).find('#notePredicateLabel').text(predicate);
        $(e.currentTarget).find('#noteDef').text(note);
        $(e.currentTarget).find('#noteDefault').attr('value', note);
        $(e.currentTarget).find('#noteTrx').text(tnote);
        $(e.currentTarget).find('#noteTrxChanged').attr('value', 'false');
    });

    $('#editScopeNote').on('show.bs.modal', function(e) {
        var label = $(e.relatedTarget).data('label');
        var cpid = $(e.relatedTarget).data('cpid');
        var active = $(e.relatedTarget).data('active');
        var concept = $(e.relatedTarget).data('concept');
        var scn = $(e.relatedTarget).data('scn');
        var scne = $(e.relatedTarget).data('scne');
        var scnt = $(e.relatedTarget).data('scnt');
        var enable_scn = $(e.relatedTarget).data('enable');

        var title = label + ' <small class="text-muted">' + cpid + '</small>';

        $(e.currentTarget).find('#scopeNoteLabel').html(title);
        $(e.currentTarget).find('#conceptScopeNote').attr('value', concept);
        $(e.currentTarget).find('#conceptScopeNoteLabel').attr('value', label);
        $(e.currentTarget).find('#scopeNoteTrx').text(scnt);

        $(e.currentTarget).find('#scopeNoteTrxChanged').attr('value', 'false');
        $(e.currentTarget).find('#scopeNoteEngChanged').attr('value', 'false');

        $(e.currentTarget).find('#scopeNoteTrxOriginal').attr('value', scnt);
        $(e.currentTarget).find('#scopeNoteEngOriginal').attr('value', scne);

        if (enable_scn) {
          $(e.currentTarget).find('#scopeNoteDef').text('');
          $(e.currentTarget).find('#scopeNoteEngGroup').show();
          $(e.currentTarget).find('#scopeNoteEng').text(scne);
        } else {
          $(e.currentTarget).find('#scopeNoteEng').text('');
          $(e.currentTarget).find('#scopeNoteEngGroup').hide();
          $(e.currentTarget).find('#scopeNoteDef').text(scn);
          $(e.currentTarget).find('#scopeNoteDefault').attr('value', scn);
        }

         if (active === false) {
          $(e.currentTarget).find('#editScopeNoteSave').attr('disabled','');
          $(e.currentTarget).find('#editScopeNoteProp').attr('disabled','');
          $(e.currentTarget).find('#scopeNoteEng').attr('disabled','');
          $(e.currentTarget).find('#scopeNoteTrx').attr('disabled','');
        } else {
          $(e.currentTarget).find('#editScopeNoteSave').removeAttr('disabled');
          $(e.currentTarget).find('#editScopeNoteProp').removeAttr('disabled');
          $(e.currentTarget).find('#scopeNoteEng').removeAttr('disabled');
          $(e.currentTarget).find('#scopeNoteTrx').removeAttr('disabled');
        }

    });

    $('#showHistoryModal').on('show.bs.modal', function(e) {
        var label = $(e.relatedTarget).data('label');
        var event = $(e.relatedTarget).data('event');
        var dui = $(e.relatedTarget).data('dui');
        var cui = $(e.relatedTarget).data('cui');
        var backlink = $(e.relatedTarget).data('backlink');
        var tstate = $(e.relatedTarget).data('tstate');
        var tstate_rep = $(e.relatedTarget).data('rstate');
        var resolvedby = $(e.relatedTarget).data('resolvedby');
        var updated = $(e.relatedTarget).data('updated');
        var anote = $(e.relatedTarget).data('note');
        var apid = $(e.relatedTarget).data('apid');
        var params = $(e.relatedTarget).data('params');
        var terms_old = $(e.relatedTarget).data('terms-old');
        var terms_new = $(e.relatedTarget).data('terms-new');
        var scnt_new = $(e.relatedTarget).data('scnt-new');
        var scnt_old = $(e.relatedTarget).data('scnt-old');
        var scn_new = $(e.relatedTarget).data('scn-new');
        var scn_old = $(e.relatedTarget).data('scn-old');

        if (resolvedby == 'None') {
          var resby = '';
        } else {
          var resby = resolvedby;
        }       

        var descpage = $(e.currentTarget).find('#updateAuditForm').data('descpage');

        /* var tstate_rep = get_statRep(tstate); */

        var title = '<a href="'+ descpage + 'dui:' + dui + '" title="Edit descriptor" aria-label="Edit descriptor">' + label +
                    ' <i class="fas fa-pen"></i></a> <br /><span class="badge badge-secondary tree-view-badge mt-2">' + event + '</span> ' +
                    '   ' + resby + '  ' +
                    '<span class="badge badge-' + tstate_rep + ' ">' + tstate + '</span> ' + '  ' + updated;

        $(e.currentTarget).find('#historyDetailTitle').html(title);
        $(e.currentTarget).find('#historyParams').html(wrapStrPre(params));
        $(e.currentTarget).find('#historyTermsOld').html(wrapStrPre(terms_old));
        $(e.currentTarget).find('#historyTermsNew').html(wrapStrPre(terms_new));
        $(e.currentTarget).find('#updateAuditApid').attr('value', apid);
        $(e.currentTarget).find('#updateAuditEvent').attr('value', event);
        $(e.currentTarget).find('#updateAuditCui').attr('value', cui);
        $(e.currentTarget).find('#updateAuditDui').attr('value', dui);
        $(e.currentTarget).find('#updateAuditBack').attr('value', backlink);

        if (!scnt_new) var scnt_new = '';
        if (!scnt_old) var scnt_old = '';
        if (!scn_new) var scn_new = '';
        if (!scn_old) var scn_old = '';

        $(e.currentTarget).find('#historyScntNew').text(scnt_new);
        $(e.currentTarget).find('#historyScntOld').text(scnt_old);
        $(e.currentTarget).find('#historyScnNew').text(scn_new);
        $(e.currentTarget).find('#historyScnOld').text(scn_old);

        if (tstate == 'pending') {
          $(e.currentTarget).find('#auditRejectButt').show();
          $(e.currentTarget).find('#auditApproveButt').show();

        } else {
          $(e.currentTarget).find('#auditRejectButt').hide();
          $(e.currentTarget).find('#auditApproveButt').hide();
          if (anote == 'None') var anote = '';
            $(e.currentTarget).find('#noteAudit').text(anote);
            $(e.currentTarget).find('#noteAuditLabel').text(anote);
        }
    });

    $('#modify-user-modal').on('show.bs.modal', function(e) {
        var formid = $(e.currentTarget).data('formid');

        var userid = $(e.relatedTarget).data('userid');
        var firstname = $(e.relatedTarget).data('firstname');
        var lastname = $(e.relatedTarget).data('lastname');
        var username = $(e.relatedTarget).data('username');
        var ugroup = $(e.relatedTarget).data('ugroup');
        var email = $(e.relatedTarget).data('email');
        var phone = $(e.relatedTarget).data('phone');
        var updated = $(e.relatedTarget).data('updated');

        $(e.currentTarget).find('#ugroup-'+ formid).val(ugroup).change();

        $(e.currentTarget).find('#updatedUserName').text(username);
        $(e.currentTarget).find('#userLastUpdate').text('Updated  '+updated);

        $(e.currentTarget).find('#uname-'+ formid).val(username);
        $(e.currentTarget).find('#userid-'+ formid).val(userid);
        $(e.currentTarget).find('#firstname-'+ formid).val(firstname);
        $(e.currentTarget).find('#lastname-'+ formid).val(lastname);
        $(e.currentTarget).find('#email-'+ formid).val(email);
        $(e.currentTarget).find('#phone-'+ formid).val(phone);

        var curname = $(e.currentTarget).data('curuser');
        if (username == curname) {
          $(e.currentTarget).find('#deleteUserButton').attr('disabled','');
        } else {
          $(e.currentTarget).find('#deleteUserButton').removeAttr('disabled');
          $(e.currentTarget).find('#deleteUserButton').attr('title',username);
        }
    });

    $('#deleteUser').on('show.bs.modal', function(e) {
        var target = $(e.relatedTarget).data('form');
        var uname = $(e.relatedTarget).attr('title');

        $(e.currentTarget).find('#delUserName').text(uname);
        $(this).find('#confirmDeleteUserButton').attr('title', target);
    });

    $('#confirmDeleteUserButton').click(function() {
        var target = $(this).attr('title');
        $($.find(target+'-action')).attr('value', 'delete');
        $($.find(target+'-form')).submit();
    });

});


// Functions

/* 
Wrap a string with <pre> tag
*/
function wrapStrPre(mystr) {
    if (mystr) {
        return '<pre>' + mystr + '</pre>';
    } else {
        return '';
    }
}

/*
function get_statRep(status) {
    var sRep = {
        'pending'  : "info",
        'rejected' : "danger",
        'approved' : "success",
        'updated'  : "secondary",
        'deleted'  : "dark",
        'purged'   : "light",
        'locked'   : "warning",
        'unlocked' : "primary"
        };

    return sRep[status];
};
*/
