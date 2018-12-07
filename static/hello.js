function form_check(event){
  console.log(event.target)
  let input_elem = event.target
  console.log(input_elem.name)
  // change color
}

function print_hello() {
  let fields = document.getElementsByClassName("form-control");
  for (let field of fields) {
    field.addEventListener('input', hello )
  }
}

function check_form(){
  let fields = document.getElementsByClassName("form-control");
  for (let field of fields) {
    field.addEventListener('input', form_check )

  }
}


// MAIN

check_form()
