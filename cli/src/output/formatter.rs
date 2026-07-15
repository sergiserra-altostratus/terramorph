use colored::Colorize;

pub fn print_header(title: &str) {
    println!("\n{}", title.bold());
    println!("{}", "─".repeat(title.len()));
}

pub fn print_success(msg: &str) {
    println!("{} {}", "✓".green(), msg);
}

pub fn print_error(msg: &str) {
    eprintln!("{} {}", "✗".red(), msg);
}

pub fn print_info(msg: &str) {
    println!("{} {}", "●".blue(), msg);
}
