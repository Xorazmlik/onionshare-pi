function unhumanize(text) {
  var powers = {'b': 0, 'k': 1, 'm': 2, 'g': 3, 't': 4};
  var regex = /(\d+(?:\.\d+)?)\s?(B|K|M|G|T)?/i;
  var res = regex.exec(text);
  if (res[2] === undefined) {
    return text;
  } else {
    return res[1] * Math.pow(1024, powers[res[2].toLowerCase()]);
  }
}
function sortTable(n) {
  var table, rows, switching, i, x, y, valX, valY, shouldSwitch, dir, switchcount = 0;
  table = document.getElementById('file-list');
  switching = true;
  dir = 'asc';
  while (switching) {
    switching = false;
    rows = table.getElementsByClassName('row');
    for (i = 1; i < (rows.length - 1); i++) {
      shouldSwitch = false;
      x = rows[i].getElementsByClassName('cell-data')[n];
      y = rows[i + 1].getElementsByClassName('cell-data')[n];
      valX = x.classList.contains('size') ? unhumanize(x.innerHTML.toLowerCase()) : x.innerHTML;
      valY = y.classList.contains('size') ? unhumanize(y.innerHTML.toLowerCase()) : y.innerHTML;
      if (dir == 'asc') {
        if (valX > valY) {
          shouldSwitch = true;
          break;
        }
      } else if (dir == 'desc') {
        if (valX < valY) {
          shouldSwitch = true;
          break;
        }
      }
    }
    if (shouldSwitch) {
      rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
      switching = true;
      switchcount++;
    } else {
      if (switchcount == 0 && dir == 'asc') {
        dir = 'desc';
        switching = true;
      }
    }
  }
}
document.getElementById('filename-header').addEventListener('click', function () {
  sortTable(0);
});
document.getElementById('size-header').addEventListener('click', function () {
  sortTable(1);
});
