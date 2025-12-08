library(tidyverse)
library(dplyr)
library(png)
library(grid)
library(ggplot2)
library(gganimate)

df_csv <- read.csv("player_positions.csv")|> filter(tick %% 32 == 0 | is_firing == "True")
df <- df_csv

df$len <- ifelse(df$is_firing, 100, 40)
df$map_x <- ((df$X + 3240)/5.02) * 2
df$map_y <- ((df$Y + 3410)/5.02) * 2

df$lend_x <- df$map_x + (df$len * cos(df$yaw * (pi / 180)))
df$lend_y <- df$map_y + (df$len * sin(df$yaw * (pi / 180)))



df$color <- ifelse(df$name == "KasaK", ifelse(df$team_num == "3", "ChCT", "ChT"), df$team_num)

img <- readPNG("maps/de_mirage/radar.png")

rad_bg <- rasterGrob(img, width=unit(1,"npc"), height=unit(1,"npc"), interpolate = TRUE)

r <- ggplot(df, aes(x = map_x, y=map_y, group=steamid)) + 
  
  annotation_custom(rad_bg, xmin=0, xmax=2048, ymin=0, ymax=2048) +
  geom_segment(data = subset(df, is_alive == "True"), 
               aes(xend = lend_x, yend = lend_y, color= color), 
               alpha = 0.5, size = 1) + 
  
  geom_point(aes(color=color, shape= is_alive), size=4) + 
  scale_color_manual(
    values = c("2" = "orange", "3" = "blue", "ChT" = "#f55a42", "ChCT" = "#a442f5"), 
    labels = c("2" = "T", "3" = "CT", "ChT" = "Cheater T side", "ChCT" = "Cheater CT side"),
    name = "Side"
  )+
  scale_shape_manual(
    values = c("True" = 19, "False" = 4),
    name = "Is alive"
  )+
  theme_void() +
  coord_fixed(xlim = c(0, 2048), ylim = c(0, 2048))
  


a <- r + transition_time(tick)

animate(a, renderer = gifski_renderer(), fps =20, duration = 150)

options(ggplot2.discrete.fill = FALSE)

anim_save(
  "radar.gif",
  animation = a,
  renderer = gifski_renderer(),
  fps = 20,
  duration = 150
)


