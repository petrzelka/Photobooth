breite = 350;
hoehe = 500;
tiefe = 220;
d = 8;
border = 40;

lcd_w = 235;
lcd_h = 145;
lcd_offset = 150;

// Front
translate([-border/2,0,0])
difference() {
    color("Tan") cube([breite+border, d, hoehe + border/2]);
    // LCD
    translate([breite/2+border/2, 0, hoehe-lcd_offset]) 
        cube([lcd_w, d*10, lcd_h], center=true);
    // Kamera
    translate([breite/2+border/2, 0, hoehe-lcd_offset+lcd_h/2+20]) 
        rotate([90,0,0]) cylinder(d=7, h=100, center=true);
    // Drucker
    translate([breite/2+border/2,0,25/2+d]) 
        cube([130, 100, 25], center=true);
}
// Buttons
translate([breite/2-lcd_w/3,0,hoehe-lcd_offset-lcd_h/2-60])
    rotate([90,0,0]) color("yellow") cylinder(d=60, h=20, center=true);
translate([breite/2+lcd_w/3,0,hoehe-lcd_offset-lcd_h/2-60])
    rotate([90,0,0]) color("green") cylinder(d=60, h=20, center=true);

// Rückwand
translate([0,tiefe,0])
    rotate([0,0,45]) {
        difference() {
            color("Moccasin") cube([breite, d, hoehe]);
            translate([breite/2+border/2,0,25/2+d]) 
                cube([130, 100, 25], center=true);
        }
    }
// Links    
translate([0,0,0]) {
    color("Moccasin") cube([d, tiefe, hoehe]);
    translate([-20, tiefe/2, 40])
        color("Silver") cube([40,120,40], center=true);
    translate([-20, tiefe/2, hoehe-40])
        color("Silver") cube([40,120,40], center=true);
}
// Rechts    
translate([breite-d,0,0]) {
    color("Moccasin") cube([d, tiefe, hoehe]);
    translate([20+d, tiefe/2, 40])
        color("Silver") cube([40,120,40], center=true);
    translate([20+d, tiefe/2, hoehe-40])
        color("Silver") cube([40,120,40], center=true);
}

// Boden    
translate([0,0,0])
    color("Moccasin") cube([breite, tiefe, d]);

// Deckel
translate([0,0, hoehe-d])
    color("Moccasin") cube([breite, tiefe, d]);
    
// Drucker
translate([breite/2+border/2,160/2+d, d+60/2])
    color("DarkSlateGray") cube([180, 160, 60], center=true);