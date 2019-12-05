
translate([50,0,0]) {
    translate([0,-2,0]) winkel(25, 30, 100);
    translate([-44,0,0]) rotate([0,0,-90]) winkel(25, 30, 44+2);
    translate([0,-4,0]) cube([4,4,25]);
}

translate([-30,0,0]) {
    translate([0,-2,0]) mirror([1,0,0]) winkel(25, 30, 100);
    translate([-2,0,0]) rotate([0,0,-90]) winkel(25, 30, 18+2);
    translate([-4,-4,0]) cube([4,4,25]);
}

module winkel(w, h, l) {
    t = 2;
    skrew = 3;

    difference() {
        cube([w,l,h]);
        translate([t,t,t]) cube([w,l-2*t,h]);
        translate([w,-5,0]) rotate([0,-45,0]) cube([w+10, l+10,h+10]);
        
        if(l < 30) {
            translate([w/2,l/2,0]) {
                hull() {
                    translate([-w/6,0,0]) {
                        cylinder(d=skrew, h=3*t, $fn=50, center=true);
                    }
                    translate([w/6,0,0]) {
                        cylinder(d=skrew, h=3*t, $fn=50, center=true);
                    }
                }
                hull() {
                    translate([-w/6,0,t]) {
                        cylinder(d1=skrew, d2=2*skrew, h=skrew/2, $fn=50, center=true);
                    }
                    translate([w/6,0,t]) {
                        cylinder(d1=skrew, d2=2*skrew, h=skrew/2, $fn=50, center=true);
                    }
                }
            }
        } else {     
            for(i=[l/4,l/4,l*3/4]) {
                translate([w/2,i,0]) {
                    hull() {
                        translate([-w/6,0,0]) {
                            cylinder(d=skrew, h=3*t, $fn=50, center=true);
                        }
                        translate([w/6,0,0]) {
                            cylinder(d=skrew, h=3*t, $fn=50, center=true);
                        }
                    }
                    hull() {
                        translate([-w/6,0,t]) {
                            cylinder(d1=skrew, d2=2*skrew, h=skrew/2, $fn=50, center=true);
                        }
                        translate([w/6,0,t]) {
                            cylinder(d1=skrew, d2=2*skrew, h=skrew/2, $fn=50, center=true);
                        }
                    }
                }
            }
        }
    }
}